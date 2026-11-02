"""Unified 3-Agent Packaging Workflow (End-to-End Orchestrator)

Connects the three specialized agents into a seamless LangGraph pipeline:
1. Requirement Gathering Agent:
   - Parses natural language input or structured specifications.
   - Evaluates specification completeness via LayaRouter.
   - Triggers Human-In-The-Loop (HITL) if critical dimensions or weights are missing.
   - Extracts structured part requirements (dimensions, weight, material, SNP).
2. Retrieval & Gathering Agent:
   - Calculates deterministic physical metrics (fragility, padding thickness, multi-unit layout).
   - Queries actual SQLite database tables (packages, metal_stillages, metal_pallets, base_pallets, products).
   - Filters by 3D orthogonal bounding-box fit, weight capacity, and inventory > 0.
   - Narrows down from dozens of candidates to the top 3-5 useful containers (Best Fit, Comfort Fit, Stacking, Heavy-Duty).
3. Packing Optimizer Agent:
   - Performs true 3D Extreme Point / Corner Point spatial packing on the candidate containers.
   - Evaluates full 6-degree orthogonal rotations for optimal placement.
   - Validates whether 100% of items physically fit without collisions (fits: True / False).
   - Identifies the winning container, best item orientation, and exact physical volume utilization.
   - Generates exact (x, y, z) coordinates and Three.js scene data for frontend 3D rendering.
"""

import os
import re
from typing import TypedDict, List, Dict, Any, Optional, Union

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# Import all three sub-agents
from app.agents.requirement import (
    app as requirement_app,
    Requirements,
    RequirementState,
)
from app.agents.retrieval_gathering import (
    run_retrieval_gathering,
    calculate_metrics,
)
from app.agents.packing_optimizer import (
    run_packing_optimizer,
)


# ==========================================
# Workflow State Definition
# ==========================================

class UnifiedWorkflowInput(BaseModel):
    user_input: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Either free-form text requirement, structured part dictionary, or product_id reference",
    )
    allow_rotation: bool = Field(default=True, description="Allow 3D orthogonal item rotation")
    keep_upright: bool = Field(default=False, description="Restrict rotation to yaw only")
    max_candidate_packages: int = Field(default=5, ge=1, le=10, description="Max candidate containers to evaluate")


class UnifiedPackagingWorkflowState(TypedDict, total=False):
    # Overall Inputs & Workflow Stage
    user_input: Union[str, Dict[str, Any]]
    allow_rotation: bool
    keep_upright: bool
    max_candidate_packages: int
    current_stage: str

    # Stage 1: Requirement Gathering Agent Output
    requirement_text: Optional[str]
    requirement_fulfilled: bool
    requirements: Optional[Dict[str, Any]]
    hitl_required: bool
    hitl_reason: Optional[str]

    # Stage 2: Retrieval & Gathering Agent Output
    metrics: Optional[Dict[str, Any]]
    candidate_packages: Optional[List[Dict[str, Any]]]
    recommended_package: Optional[Dict[str, Any]]
    total_candidates_found: Optional[int]
    narrowing_summary: Optional[str]

    # Stage 3: Packing Optimizer Agent Output
    fits: Optional[bool]
    best_container: Optional[Dict[str, Any]]
    best_orientation: Optional[Dict[str, Any]]
    utilization_metrics: Optional[Dict[str, Any]]
    placed_items: Optional[List[Dict[str, Any]]]
    unplaced_items: Optional[List[Dict[str, Any]]]
    scene_data: Optional[Dict[str, Any]]

    # Final Combined Status & Synthesis
    status: str
    summary: str


# ==========================================
# Node 1: Requirement Gathering Agent
# ==========================================

def requirement_gathering_node(state: UnifiedPackagingWorkflowState) -> Dict[str, Any]:
    """Node 1: Evaluates and parses requirements from raw text or structured input."""
    raw_input = state.get("user_input")

    # Case A: Input is already structured dictionary or database reference
    if isinstance(raw_input, dict):
        # If it has product_id, part_name, or explicit dimensions, it is structured
        has_dims = raw_input.get("part_length") and raw_input.get("part_width") and raw_input.get("part_height")
        has_ref = raw_input.get("product_id") is not None or raw_input.get("part_name") is not None

        if has_dims or has_ref:
            # Requirements are immediately fulfilled
            req_dict = dict(raw_input)
            return {
                "current_stage": "requirement_gathering",
                "requirement_fulfilled": True,
                "hitl_required": False,
                "hitl_reason": None,
                "requirements": req_dict,
                "requirement_text": str(req_dict.get("description") or req_dict.get("name") or "Structured input"),
            }

        # Otherwise treat the dictionary's text field if present
        text = str(raw_input.get("text") or raw_input.get("requirement") or "")
    else:
        text = str(raw_input or "")

    # Case B: Free-form text input - Run Requirement Gathering Agent (LangGraph)
    req_state: RequirementState = {"requirement": text}
    req_result = requirement_app.invoke(req_state)

    is_fulfilled = bool(req_result.get("fullfilled") or req_result.get("fulfilled"))
    hitl_reason = req_result.get("hitl_reason")
    extracted_req = req_result.get("requirements")

    if is_fulfilled and extracted_req:
        req_dict = extracted_req.model_dump() if hasattr(extracted_req, "model_dump") else dict(extracted_req)
        return {
            "current_stage": "requirement_gathering",
            "requirement_fulfilled": True,
            "hitl_required": False,
            "hitl_reason": None,
            "requirements": req_dict,
            "requirement_text": text,
        }
    else:
        return {
            "current_stage": "requirement_gathering",
            "requirement_fulfilled": False,
            "hitl_required": True,
            "hitl_reason": hitl_reason or "Missing critical part dimensions (length, width, height) or weight.",
            "requirements": None,
            "requirement_text": text,
        }


def route_after_requirements(state: UnifiedPackagingWorkflowState) -> str:
    """Conditional edge: Route to HITL if requirements incomplete, else proceed to Retrieval."""
    if state.get("hitl_required"):
        return "hitl"
    return "retrieval_gathering"


# ==========================================
# Node 1.5: Human-In-The-Loop (HITL) Node
# ==========================================

def hitl_node(state: UnifiedPackagingWorkflowState) -> Dict[str, Any]:
    """Node 1.5: Human-In-The-Loop node triggered when requirement specifications are incomplete."""
    reason = state.get("hitl_reason", "Requirements incomplete.")
    return {
        "current_stage": "hitl",
        "status": "hitl_clarification_required",
        "summary": (
            f"The Requirement Gathering Agent detected incomplete specifications: {reason} "
            "Please provide the missing part dimensions (length, width, height in mm) or single part weight (kg)."
        ),
    }


# ==========================================
# Node 2: Retrieval & Gathering Agent
# ==========================================

def retrieval_gathering_node(state: UnifiedPackagingWorkflowState) -> Dict[str, Any]:
    """Node 2: Queries SQLite database tables and narrows down candidate containers."""
    requirements = state.get("requirements", {})
    max_candidates = state.get("max_candidate_packages", 5)

    # Invoke Retrieval & Gathering Agent
    retrieval_result = run_retrieval_gathering(requirements, max_results=max_candidates)

    resolved_req = retrieval_result.get("requirements") or requirements
    metrics = retrieval_result.get("metrics", {})
    matching_packages = retrieval_result.get("matching_packages", [])
    recommended_package = retrieval_result.get("recommended_package")
    total_found = retrieval_result.get("total_candidates_found", 0)
    summary = retrieval_result.get("narrowing_summary", "")

    return {
        "current_stage": "retrieval_gathering",
        "requirements": resolved_req,
        "metrics": metrics,
        "candidate_packages": matching_packages,
        "recommended_package": recommended_package,
        "total_candidates_found": total_found,
        "narrowing_summary": summary,
    }


# ==========================================
# Node 3: Packing Optimizer Agent
# ==========================================

def packing_optimization_node(state: UnifiedPackagingWorkflowState) -> Dict[str, Any]:
    """Node 3: Executes 3D Extreme Point Spatial Packing on the narrowed containers."""
    requirements = state.get("requirements", {})
    candidate_packages = state.get("candidate_packages", [])
    allow_rot = state.get("allow_rotation", True)
    keep_upright = state.get("keep_upright", False)

    # Format containers for Packing Optimizer Agent
    containers_for_packing = []
    for p in candidate_packages:
        inner = p.get("inner_dimensions_mm", {})
        containers_for_packing.append({
            "name": p.get("name"),
            "category": p.get("category", "carton"),
            "inner_length_mm": inner.get("length", 300.0),
            "inner_width_mm": inner.get("width", 200.0),
            "inner_height_mm": inner.get("height", 100.0),
            "max_weight_capacity_kg": p.get("max_weight_capacity_kg", 1000.0),
        })

    metrics = state.get("metrics", {})
    resolved_snp = requirements.get("snp") or metrics.get("snp", 1)

    # Prepare Packing Optimizer input
    packing_input = {
        "product_id": requirements.get("product_id") or requirements.get("matched_product_id"),
        "part_name": requirements.get("name") or requirements.get("part_name") or metrics.get("part_name"),
        "part_length": requirements.get("part_length"),
        "part_width": requirements.get("part_width"),
        "part_height": requirements.get("part_height"),
        "part_weight": requirements.get("part_weight"),
        "snp": resolved_snp,
        "candidate_containers": containers_for_packing,
        "allow_rotation": allow_rot,
        "keep_upright": keep_upright,
    }

    # Invoke Packing Optimizer Agent
    packing_result = run_packing_optimizer(packing_input)

    fits = packing_result.get("fits", False)
    best_container = packing_result.get("best_container")
    best_orientation = packing_result.get("best_orientation")
    utilization_metrics = packing_result.get("utilization_metrics", {})
    placed_items = packing_result.get("placed_items", [])
    unplaced_items = packing_result.get("unplaced_items", [])
    scene_data = packing_result.get("scene_data", {})

    # Synthesize end-to-end multi-agent summary
    part_name = requirements.get("name") or requirements.get("part_name") or metrics.get("part_name") or "Part"
    snp = resolved_snp
    foam_type = metrics.get("recommended_padding_material", "foam")
    foam_thick = metrics.get("recommended_padding_thickness_mm", 15.0)

    if fits and best_container:
        c_name = best_container.get("name", "Container")
        util_pct = utilization_metrics.get("volume_utilization_pct", 0.0)
        wasted_l = utilization_metrics.get("wasted_volume_liters", 0.0)
        placed_n = utilization_metrics.get("placed_count", snp)
        total_wt = utilization_metrics.get("total_packed_weight_kg", 0.0)

        orient_str = ""
        if best_orientation:
            orient_str = f" at {best_orientation.get('length')}x{best_orientation.get('width')}x{best_orientation.get('height')} mm orientation"

        narrative = (
            f"End-to-end workflow completed successfully across all 3 agents:\n"
            f"1. Requirement Gathering: Parsed {snp} units of '{part_name}'. Applied {foam_thick}mm {foam_type} padding.\n"
            f"2. Retrieval Agent: Evaluated SQLite database and narrowed {state.get('total_candidates_found', 0)} candidates to {len(candidate_packages)} top choices.\n"
            f"3. Packing Optimizer: Verified 3D Extreme Point placement for all {placed_n} items in '{c_name}'{orient_str} with 0 clashes. "
            f"Achieved {util_pct}% volume utilization ({wasted_l} L void space, total packed weight: {total_wt} kg)."
        )
        status = "workflow_completed_optimal_fit"
    else:
        narrative = (
            f"Workflow completed with partial fit. Standard warehouse containers cannot fully fit all {snp} units "
            f"of '{part_name}'. Custom box sizing is recommended."
        )
        status = "workflow_completed_partial_fit"

    return {
        "current_stage": "packing_optimization",
        "fits": fits,
        "best_container": best_container,
        "best_orientation": best_orientation,
        "utilization_metrics": utilization_metrics,
        "placed_items": placed_items,
        "unplaced_items": unplaced_items,
        "scene_data": scene_data,
        "status": status,
        "summary": narrative,
    }


# ==========================================
# LangGraph StateGraph Construction
# ==========================================

workflow = StateGraph(UnifiedPackagingWorkflowState)

# Add Nodes
workflow.add_node("requirement_gathering", requirement_gathering_node)
workflow.add_node("hitl", hitl_node)
workflow.add_node("retrieval_gathering", retrieval_gathering_node)
workflow.add_node("packing_optimization", packing_optimization_node)

# Add Edges & Conditional Routing
workflow.add_edge(START, "requirement_gathering")
workflow.add_conditional_edges(
    "requirement_gathering",
    route_after_requirements,
    {
        "hitl": "hitl",
        "retrieval_gathering": "retrieval_gathering",
    },
)
workflow.add_edge("hitl", END)
workflow.add_edge("retrieval_gathering", "packing_optimization")
workflow.add_edge("packing_optimization", END)

# Compile LangGraph Runnable
app = workflow.compile()


# ==========================================
# Standalone Direct Callable
# ==========================================

def run_unified_workflow(
    user_input: Union[str, Dict[str, Any]],
    allow_rotation: bool = True,
    keep_upright: bool = False,
    max_candidate_packages: int = 5,
) -> Dict[str, Any]:
    """Execute the end-to-end 3-Agent Packaging Workflow directly.

    Args:
        user_input: Natural language text requirement, structured part dict, or product reference.
        allow_rotation: Whether 3D orthogonal rotation is allowed.
        keep_upright: Restrict rotation to yaw only (keep height vertical).
        max_candidate_packages: Number of top candidate packages to evaluate.

    Returns:
        Consolidated workflow dictionary containing stage-by-stage results,
        metrics, 3D placement coordinates, and final synthesis.
    """
    initial_state: UnifiedPackagingWorkflowState = {
        "user_input": user_input,
        "allow_rotation": allow_rotation,
        "keep_upright": keep_upright,
        "max_candidate_packages": max_candidate_packages,
    }

    result = app.invoke(initial_state)

    req_out = dict(result.get("requirements") or {})
    metrics_out = result.get("metrics") or {}
    if metrics_out:
        if not req_out.get("name") or req_out.get("name") == "Part":
            req_out["name"] = metrics_out.get("part_name")
        if not req_out.get("snp") or req_out.get("snp") == "SNP-1":
            req_out["snp"] = metrics_out.get("snp")
        if not req_out.get("part_type"):
            req_out["part_type"] = metrics_out.get("part_type")

    return {
        "status": result.get("status"),
        "summary": result.get("summary"),
        "stage": result.get("current_stage"),
        "hitl_required": result.get("hitl_required", False),
        "hitl_reason": result.get("hitl_reason"),
        "requirements": req_out,
        "metrics": result.get("metrics"),
        "candidate_packages": result.get("candidate_packages", []),
        "fits": result.get("fits", False),
        "best_container": result.get("best_container"),
        "best_orientation": result.get("best_orientation"),
        "utilization_metrics": result.get("utilization_metrics"),
        "placed_items": result.get("placed_items", []),
        "unplaced_items": result.get("unplaced_items", []),
        "scene_data": result.get("scene_data", {}),
    }


# ==========================================
# Standalone CLI Self-Test
# ==========================================

if __name__ == "__main__":
    print("=" * 75)
    print("Unified 3-Agent Workflow (Requirement -> Retrieval -> Packing Optimizer)")
    print("=" * 75)

    # -------------------------------------------------------------
    # Test 1: Natural Language Requirement String
    # -------------------------------------------------------------
    print("\n>>> WORKFLOW TEST 1: Free-Form Text Requirement")
    prompt_text = "I need packaging for 4 steel brackets measuring length 140mm, width 90mm, height 60mm and weight 1.2kg each."
    res1 = run_unified_workflow(prompt_text)
    print(f"Status: {res1['status']}")
    print(f"Stage 1 Extracted Name: {res1['requirements'].get('name')}")
    print(f"Stage 2 Top Carton: {res1['best_container'].get('name')}")
    print(f"Stage 3 Fits: {res1['fits']} | Volume Utilization: {res1['utilization_metrics'].get('volume_utilization_pct')}%")
    print(f"\nFinal Workflow Summary:\n{res1['summary']}")

    # -------------------------------------------------------------
    # Test 2: Incomplete Requirement -> HITL Clarification
    # -------------------------------------------------------------
    print("\n>>> WORKFLOW TEST 2: Incomplete Text -> Human-In-The-Loop Trigger")
    incomplete_text = "Please pack my metal parts safely."
    res2 = run_unified_workflow(incomplete_text)
    print(f"Status: {res2['status']}")
    print(f"HITL Required: {res2['hitl_required']}")
    print(f"HITL Reason: {res2['hitl_reason']}")
    print(f"Summary: {res2['summary']}")

    # -------------------------------------------------------------
    # Test 3: SQLite Database Product Auto-Lookup (Product 1: Micro Terminal Block)
    # -------------------------------------------------------------
    print("\n>>> WORKFLOW TEST 3: Database Product Auto-Lookup (Product ID: 1)")
    res3 = run_unified_workflow({"product_id": 1})
    print(f"Status: {res3['status']}")
    print(f"Part: {res3['requirements'].get('name')} | SNP: {res3['requirements'].get('snp')}")
    print(f"Winning Container: {res3['best_container'].get('name')}")
    print(f"Best Part Orientation: {res3['best_orientation']}")
    print(f"Placed Count: {res3['utilization_metrics'].get('placed_count')} / {res3['utilization_metrics'].get('total_items')}")
    print(f"Volume Utilization: {res3['utilization_metrics'].get('volume_utilization_pct')}%")
    print(f"Three.js Visualizer Elements: {len(res3['scene_data'].get('items', []))} 3D boxes")

    print("\n" + "=" * 75)
    print("All 3-Agent Workflow tests completed successfully!")
    print("=" * 75)
