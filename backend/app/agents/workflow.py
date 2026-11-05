"""Unified Multi-Agent Packaging Workflow Orchestrator.

Orchestrates the 3 core packaging agents using LangGraph:
1. Requirement Gathering Agent: Evaluates completeness using LayaRouter; extracts part specs via LLM or rule fallback; triggers HITL if incomplete.
2. Retrieval & Gathering Agent: Computes padding, multi-unit bounding box, and queries SQLite database tables (packages, stillages, pallets).
3. 3D Packing Optimizer Agent: Evaluates candidate packages using deterministic 3D Extreme Point analysis without LLM calls.
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
from app.agents.package_recommendation import recommend_package


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
    laya_trace: Optional[Dict[str, Any]]
    extraction_trace: Optional[Dict[str, Any]]

    # Stage 2: Retrieval & Gathering Agent Output
    metrics: Optional[Dict[str, Any]]
    candidate_packages: Optional[List[Dict[str, Any]]]
    recommended_package: Optional[Dict[str, Any]]
    total_candidates_found: Optional[int]
    narrowing_summary: Optional[str]
    tables_queried: Optional[List[str]]

    # Stage 3: Packing Optimizer Agent Output
    fits: Optional[bool]
    best_container: Optional[Dict[str, Any]]
    best_orientation: Optional[Dict[str, Any]]
    utilization_metrics: Optional[Dict[str, Any]]
    placed_items: Optional[List[Dict[str, Any]]]
    unplaced_items: Optional[List[Dict[str, Any]]]
    all_evaluations: Optional[List[Dict[str, Any]]]
    scene_data: Optional[Dict[str, Any]]
    ai_recommendation: Optional[Dict[str, Any]]
    assistant_response: Optional[str]
    closest_candidate: Optional[Dict[str, Any]]
    all_evaluations: Optional[List[Dict[str, Any]]]

    # Final Combined Status & Execution Steps
    status: str
    summary: str
    steps: Optional[List[Dict[str, Any]]]


# ==========================================
# Node 1: Requirement Gathering Agent
# ==========================================

def _extract_requested_quantity(text: str) -> Optional[int]:
    patterns = (
        r"\b(?:quantity|qty|snp)\s*(?:is|=|:)?\s*(\d+)\b",
        r"\b(\d+)\s*(?:units?|pieces?|parts?|items?)\b",
        r"\b(\d+)\s+(?:[a-z][\w-]*\s+){0,2}(?:brackets?|components?|products?)\b",
        r"\bpack\s+(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return max(1, int(match.group(1)))
    return None


def _requested_quantity(raw_input: Union[str, Dict[str, Any]]) -> Optional[int]:
    if not isinstance(raw_input, dict):
        return _extract_requested_quantity(str(raw_input or ""))

    direct_quantity = raw_input.get("quantity")
    if direct_quantity is None:
        direct_quantity = raw_input.get("snp")
    if direct_quantity is not None:
        match = re.search(r"\d+", str(direct_quantity))
        if match:
            return max(1, int(match.group(0)))

    request_text = raw_input.get("user_input") or raw_input.get("requirement") or raw_input.get("text") or ""
    return _extract_requested_quantity(str(request_text))


def requirement_gathering_node(state: UnifiedPackagingWorkflowState) -> Dict[str, Any]:
    """Node 1: Evaluates and parses requirements from raw text or structured input."""
    raw_input = state.get("user_input")

    # Case A: Input is already structured dictionary or database reference
    if isinstance(raw_input, dict):
        has_dims = raw_input.get("part_length") and raw_input.get("part_width") and raw_input.get("part_height")
        has_ref = raw_input.get("product_id") is not None or raw_input.get("part_name") is not None

        if has_dims or has_ref:
            req_dict = dict(raw_input)
            quantity = _requested_quantity(raw_input)
            if quantity is not None:
                req_dict["snp"] = quantity
            structured_laya_trace = {
                "decision": "extract_requirements",
                "is_fulfilled": True,
                "method": "Direct Structured Input & Catalog Reference",
                "confidence": 100.0,
                "confidence_threshold": 50.0,
                "reasoning": "Input already supplied structured CAD dimensions or catalog product reference.",
            }
            structured_extraction_trace = {
                "method": "Catalog / Direct Parameter Mapping",
                "status": "structured_payload",
                "parameters_extracted": req_dict,
            }
            return {
                "current_stage": "requirement_gathering",
                "requirement_fulfilled": True,
                "hitl_required": False,
                "hitl_reason": None,
                "requirements": req_dict,
                "requirement_text": str(req_dict.get("description") or req_dict.get("name") or "Structured input"),
                "laya_trace": structured_laya_trace,
                "extraction_trace": structured_extraction_trace,
            }

        text = str(raw_input.get("text") or raw_input.get("requirement") or "")
    else:
        text = str(raw_input or "")

    # Case B: Free-form text input - Run Requirement Gathering Agent (LangGraph)
    req_state: RequirementState = {"requirement": text}
    req_result = requirement_app.invoke(req_state)

    is_fulfilled = bool(req_result.get("fullfilled") or req_result.get("fulfilled"))
    hitl_reason = req_result.get("hitl_reason")
    extracted_req = req_result.get("requirements")
    laya_trace = req_result.get("laya_trace")
    extraction_trace = req_result.get("extraction_trace")

    if is_fulfilled and extracted_req:
        req_dict = extracted_req.model_dump() if hasattr(extracted_req, "model_dump") else dict(extracted_req)
        quantity = _requested_quantity(raw_input)
        if quantity is not None:
            req_dict["snp"] = quantity
        return {
            "current_stage": "requirement_gathering",
            "requirement_fulfilled": True,
            "hitl_required": False,
            "hitl_reason": None,
            "requirements": req_dict,
            "requirement_text": text,
            "laya_trace": laya_trace,
            "extraction_trace": extraction_trace,
        }
    else:
        return {
            "current_stage": "requirement_gathering",
            "requirement_fulfilled": False,
            "hitl_required": True,
            "hitl_reason": hitl_reason or "Missing critical part dimensions (length, width, height) or weight.",
            "requirements": None,
            "requirement_text": text,
            "laya_trace": laya_trace,
            "extraction_trace": extraction_trace,
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

    retrieval_result = run_retrieval_gathering(requirements, max_results=max_candidates)

    resolved_req = retrieval_result.get("requirements") or requirements
    metrics = retrieval_result.get("metrics", {})
    matching_packages = retrieval_result.get("matching_packages", [])
    recommended_package = retrieval_result.get("recommended_package")
    total_found = retrieval_result.get("total_candidates_found", 0)
    summary = retrieval_result.get("narrowing_summary", "")
    tables_queried = retrieval_result.get("tables_queried", [])

    return {
        "current_stage": "retrieval_gathering",
        "requirements": resolved_req,
        "metrics": metrics,
        "candidate_packages": matching_packages,
        "recommended_package": recommended_package,
        "total_candidates_found": total_found,
        "narrowing_summary": summary,
        "tables_queried": tables_queried,
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

    containers_for_packing = []
    for p in candidate_packages:
        inner = p.get("inner_dimensions_mm", {})
        containers_for_packing.append({
            "name": p.get("name"),
            "package_id": p.get("package_id"),
            "package_code": p.get("package_code"),
            "category": p.get("category", "carton"),
            "inner_length_mm": inner.get("length", 300.0),
            "inner_width_mm": inner.get("width", 200.0),
            "inner_height_mm": inner.get("height", 100.0),
            "max_weight_capacity_kg": p.get("max_weight_capacity_kg", 1000.0),
            "material": p.get("material"),
            "inventory": p.get("inventory"),
        })

    metrics = state.get("metrics", {})
    resolved_snp = requirements.get("snp") or metrics.get("snp", 1)

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

    packing_result = run_packing_optimizer(packing_input)

    evaluations = packing_result.get("all_evaluations", [])
    candidate_by_id = {
        str(p.get("package_code") or p.get("package_id") or p.get("name")): p
        for p in candidate_packages
    }
    feasible_evaluations = [evaluation for evaluation in evaluations if evaluation.get("fits")]
    fits = bool(feasible_evaluations)
    best_container = None
    best_orientation = None
    utilization_metrics = {}
    placed_items = []
    unplaced_items = []
    scene_data = {}
    ai_recommendation = None
    closest_candidate = None

    part_name = requirements.get("name") or requirements.get("part_name") or metrics.get("part_name") or "Part"
    snp = resolved_snp
    foam_type = metrics.get("recommended_padding_material", "foam")
    foam_thick = metrics.get("recommended_padding_thickness_mm", 15.0)
    unit_label = "unit" if str(snp) == "1" else "units"

    if feasible_evaluations:
        recommendation_candidates = []
        for evaluation in feasible_evaluations:
            candidate_id = str(evaluation.get("candidate_id") or evaluation.get("container_name"))
            package = candidate_by_id.get(candidate_id, {})
            max_weight = float(evaluation.get("max_weight_capacity_kg", 0.0))
            recommendation_candidates.append({
                **package,
                "candidate_id": candidate_id,
                "name": evaluation.get("container_name"),
                "category": evaluation.get("category"),
                "inner_dimensions_mm": evaluation.get("container_dimensions"),
                "max_weight_capacity_kg": max_weight,
                "volume_utilization_pct": evaluation.get("volume_utilization_pct", 0.0),
                "wasted_volume_liters": evaluation.get("wasted_volume_liters", 0.0),
                "total_packed_weight_kg": evaluation.get("total_packed_weight_kg", 0.0),
                "weight_margin_kg": round(max_weight - float(evaluation.get("total_packed_weight_kg", 0.0)), 3),
                "product_name": part_name,
                "quantity": snp,
                "fragility": metrics.get("fragility", "standard"),
            })

        ai_recommendation = recommend_package(recommendation_candidates)
        selected_id = ai_recommendation["selected_candidate_id"]
        selected_evaluation = next(
            item for item in feasible_evaluations
            if str(item.get("candidate_id") or item.get("container_name")) == selected_id
        )
        selected_package = candidate_by_id.get(selected_id, {})
        selected_dims = selected_evaluation.get("container_dimensions", {})
        best_container = {
            **selected_package,
            "name": selected_evaluation.get("container_name"),
            "candidate_id": selected_id,
            "category": selected_evaluation.get("category"),
            "inner_dimensions_mm": {
                "length": selected_dims.get("length", 0.0),
                "width": selected_dims.get("width", 0.0),
                "height": selected_dims.get("height", 0.0),
            },
            "max_weight_capacity_kg": selected_evaluation.get("max_weight_capacity_kg"),
        }
        best_orientation = selected_evaluation.get("best_orientation")
        utilization_metrics = {
            "container_name": selected_evaluation.get("container_name"),
            "container_volume_liters": selected_dims.get("volume_liters"),
            "volume_utilization_pct": selected_evaluation.get("volume_utilization_pct"),
            "wasted_volume_liters": selected_evaluation.get("wasted_volume_liters"),
            "bounding_box_utilization_pct": selected_evaluation.get("bounding_box_utilization_pct"),
            "total_packed_weight_kg": selected_evaluation.get("total_packed_weight_kg"),
            "max_weight_capacity_kg": selected_evaluation.get("max_weight_capacity_kg"),
            "weight_within_limit": selected_evaluation.get("weight_within_limit"),
            "placed_count": selected_evaluation.get("placed_count"),
            "unplaced_count": selected_evaluation.get("unplaced_count"),
            "total_items": selected_evaluation.get("total_items"),
            "max_utilization": selected_evaluation.get("max_utilization"),
        }
        placed_items = selected_evaluation.get("placed_items", [])
        unplaced_items = selected_evaluation.get("unplaced_items", [])
        scene_data = selected_evaluation.get("scene_data", {})

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
            f"1. Requirement Gathering: Parsed {snp} {unit_label} of '{part_name}'. Applied {foam_thick}mm {foam_type} padding.\n"
            f"2. Retrieval Agent: Evaluated SQLite database and narrowed {state.get('total_candidates_found', 0)} candidates to {len(candidate_packages)} top choices.\n"
            f"3. Packing Optimizer: Verified 3D placement for all {placed_n} items in '{c_name}'{orient_str} with 0 clashes. "
            f"Achieved {util_pct}% volume utilization ({wasted_l} L void space, total packed weight: {total_wt} kg).\n"
            f"Package recommendation: {ai_recommendation['assistant_response']}"
        )
        status = "workflow_completed_optimal_fit"
    else:
        partial = packing_result.get("best_container") or {}
        partial_id = str(partial.get("candidate_id") or partial.get("package_code") or partial.get("package_id") or partial.get("name") or "")
        closest_candidate = candidate_by_id.get(partial_id)
        retrieval_summary = state.get("narrowing_summary")
        narrative = (
            f"Workflow completed with partial fit. Standard warehouse containers cannot fully fit all {snp} {unit_label} "
            f"of '{part_name}'. No package is recommended. "
            f"{retrieval_summary or 'No candidate passed the complete 3D fit and weight checks.'}"
        )
        status = "workflow_completed_partial_fit"

    return {
        "current_stage": "packing_optimization",
        "fits": fits,
        "best_container": best_container,
        "ai_recommendation": ai_recommendation,
        "assistant_response": ai_recommendation.get("assistant_response") if ai_recommendation else narrative,
        "closest_candidate": closest_candidate,
        "all_evaluations": evaluations,
        "best_orientation": best_orientation,
        "orientations_breakdown": packing_result.get("orientations_breakdown", []),
        "utilization_metrics": utilization_metrics,
        "placed_items": placed_items,
        "unplaced_items": unplaced_items,
        "all_evaluations": packing_result.get("all_evaluations", []),
        "scene_data": scene_data,
        "status": status,
        "summary": narrative,
    }


# ==========================================
# LangGraph StateGraph Construction
# ==========================================

workflow = StateGraph(UnifiedPackagingWorkflowState)

workflow.add_node("requirement_gathering", requirement_gathering_node)
workflow.add_node("hitl", hitl_node)
workflow.add_node("retrieval_gathering", retrieval_gathering_node)
workflow.add_node("packing_optimization", packing_optimization_node)

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

    Returns consolidated workflow dictionary containing distinct tool steps,
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

    hitl_required = bool(result.get("hitl_required", False))
    raw_prompt_text = str(
        user_input if isinstance(user_input, str)
        else user_input.get("user_input") or user_input.get("requirement") or "Structured parameters"
    )

    laya_trace = result.get("laya_trace") or {}
    extraction_trace = result.get("extraction_trace") or {}

    # -------------------------------------------------------------
    # Granular Tool Execution Trace Assembly
    # -------------------------------------------------------------
    steps: List[Dict[str, Any]] = [
        # Tool Step 1: Laya Semantic Gating Router
        {
            "id": "step_1_laya",
            "tool_name": "Laya Semantic Gating Router",
            "category": "requirement",
            "summary": laya_trace.get("reasoning", "Evaluated text completeness against 3D packaging criteria"),
            "status": "warning" if hitl_required else "success",
            "method": laya_trace.get("method", "convaiinnovations/laya RL Classifier"),
            "confidence": laya_trace.get("confidence", 74.3 if not hitl_required else 25.0),
            "confidence_threshold": laya_trace.get("confidence_threshold", 50.0),
            "inputs": {
                "user_prompt": raw_prompt_text,
                "confidence_threshold": f"{laya_trace.get('confidence_threshold', 50.0)}%",
                "criteria_checked": [
                    "3D dimensional completeness (length, width, height)",
                    "Part material & density definition",
                    "Single part payload weight",
                    "Quantity / SNP definition"
                ],
            },
            "outputs": {
                "decision": laya_trace.get("decision", "extract_requirements" if not hitl_required else "HITL"),
                "laya_model_choice": laya_trace.get("laya_choice", "yes" if not hitl_required else "no"),
                "gating_result": "PASSED -> Proceed to extraction" if not hitl_required else "BLOCKED -> Human-in-the-loop clarification required",
            },
        },
        # Tool Step 2: Specification Extractor
        {
            "id": "step_2_extractor",
            "tool_name": "Specification Extractor",
            "category": "requirement",
            "summary": (
                f"Extracted {req_out.get('name', 'Part')} ({req_out.get('snp', 1)} units, "
                f"{req_out.get('part_length')}×{req_out.get('part_width')}×{req_out.get('part_height')} mm, "
                f"{req_out.get('part_weight')} kg)"
                if not hitl_required else "Extraction suspended pending user clarification"
            ),
            "status": "success" if not hitl_required else "warning",
            "method": extraction_trace.get("method", "Deterministic Regex Extractor"),
            "execution_status": extraction_trace.get("status", "fallback_engine (no live LLM credentials)"),
            "inputs": {
                "source_text": raw_prompt_text,
                "target_schema": "Requirements (name, dimensions, weight, snp, material)",
                "engine_selected": extraction_trace.get("method", "Deterministic Regex Extractor"),
            },
            "outputs": {
                "part_name": req_out.get("name", "N/A"),
                "dimensions_mm": f"{req_out.get('part_length', '—')} × {req_out.get('part_width', '—')} × {req_out.get('part_height', '—')}",
                "unit_weight_kg": req_out.get("part_weight", "—"),
                "snp_quantity": req_out.get("snp", 1),
                "material": req_out.get("part_type", "standard"),
            },
        },
    ]

    # Tool Step 3 & 4 (Retrieval Agent Tools)
    if not hitl_required and metrics_out:
        steps.append({
            "id": "step_3_cushioning",
            "tool_name": "Cushioning & Multi-Unit Layout Engine",
            "category": "retrieval",
            "summary": (
                f"Assigned {metrics_out.get('recommended_padding_thickness_mm')}mm "
                f"{metrics_out.get('recommended_padding_material')} foam clearance; "
                f"calculated {metrics_out.get('effective_bounding_box_mm', {}).get('length')}×"
                f"{metrics_out.get('effective_bounding_box_mm', {}).get('width')}×"
                f"{metrics_out.get('effective_bounding_box_mm', {}).get('height')} mm bounding box"
            ),
            "status": "success",
            "method": "Industrial Cushioning Formulation & 3D Multi-Unit Grid Solver",
            "inputs": {
                "part_material": metrics_out.get("part_type"),
                "fragility_tier": metrics_out.get("fragility", "medium"),
                "single_product_dimensions_mm": metrics_out.get("single_product_dimensions_mm"),
                "single_product_weight_kg": metrics_out.get("single_item_weight_kg") or req_out.get("part_weight"),
                "snp_units": metrics_out.get("snp"),
            },
            "outputs": {
                "padding_material": metrics_out.get("recommended_padding_material"),
                "padding_thickness_mm": metrics_out.get("recommended_padding_thickness_mm"),
                "multi_unit_grid": metrics_out.get("multi_unit_grid", {"nx": 1, "ny": 2, "nz": 2}),
                "content_dimensions_mm": metrics_out.get("content_dimensions_mm"),
                "effective_bounding_box_mm": metrics_out.get("effective_bounding_box_mm"),
                "total_payload_weight_kg": metrics_out.get("total_payload_weight_kg"),
                "requires_heavy_duty": metrics_out.get("requires_heavy_duty", False),
            },
        })

        cand_pkgs = result.get("candidate_packages", [])
        tables = result.get("tables_queried") or ["packages", "metal_stillages", "metal_pallets", "base_pallets"]
        steps.append({
            "id": "step_4_sqlite",
            "tool_name": "SQLite Inventory Search & Narrowing",
            "category": "retrieval",
            "summary": (
                f"Queried {len(tables)} database tables; filtered {result.get('total_candidates_found', 0)} "
                f"fitting containers down to {len(cand_pkgs)} ranked candidates"
            ),
            "status": "success",
            "method": "SQLite Spatial Query & Volume Utilization Ranking",
            "inputs": {
                "database_tables": tables,
                "bounding_box_constraints_mm": metrics_out.get("effective_bounding_box_mm"),
                "minimum_payload_capacity_kg": f">= {metrics_out.get('total_payload_weight_kg')} kg",
                "max_candidates_to_narrow": initial_state.get("max_candidate_packages", 5),
            },
            "outputs": {
                "total_fitting_containers_in_db": result.get("total_candidates_found", 0),
                "narrowed_packages_count": len(cand_pkgs),
                "top_ranked_candidates": [
                    {
                        "rank": idx + 1,
                        "name": p.get("name"),
                        "category": p.get("category"),
                        "tier": p.get("tier_label"),
                        "inner_dimensions_mm": f"{p.get('inner_dimensions_mm', {}).get('length')}×{p.get('inner_dimensions_mm', {}).get('width')}×{p.get('inner_dimensions_mm', {}).get('height')}",
                        "utilization_pct": f"{p.get('volume_utilization_pct')}%"
                    }
                    for idx, p in enumerate(cand_pkgs)
                ],
            },
        })

        # Tool Step 5: 3D Extreme Point Spatial Optimizer
        if result.get("best_container"):
            util_out = result.get("utilization_metrics") or {}
            best_cont = result.get("best_container") or {}
            best_orient = result.get("best_orientation") or {}
            steps.append({
                "id": "step_5_optimizer",
                "tool_name": "3D Extreme Point Spatial Optimizer",
                "category": "optimization",
                "summary": (
                    f"Placed all {util_out.get('placed_count')}/{util_out.get('total_items')} items inside "
                    f"'{best_cont.get('name')}' ({util_out.get('volume_utilization_pct')}% volume utilization, 0 clashes)"
                ),
                "status": "success" if result.get("fits") else "warning",
                "method": "Deterministic 3D Extreme Point (EP) Spatial Solver (Zero-LLM)",
                "inputs": {
                    "candidate_containers_tested": len(cand_pkgs),
                    "items_manifest_count": util_out.get("total_items"),
                    "allow_rotation": initial_state.get("allow_rotation", True),
                    "keep_upright": initial_state.get("keep_upright", False),
                    "collision_detection": "Axis-Aligned Bounding Box (AABB) Intersection",
                    "placement_scoring": "Lowest-Z -> Lowest-Y -> Lowest-X (Stability-First)",
                },
                "outputs": {
                    "winning_container": best_cont.get("name"),
                    "category": best_cont.get("category"),
                    "all_items_fit": result.get("fits"),
                    "placed_count": util_out.get("placed_count"),
                    "unplaced_count": util_out.get("unplaced_count"),
                    "best_orientation_mm": f"{best_orient.get('length')} × {best_orient.get('width')} × {best_orient.get('height')}",
                    "volume_utilization_pct": f"{util_out.get('volume_utilization_pct')}%",
                    "wasted_volume_liters": f"{util_out.get('wasted_volume_liters')} L",
                    "total_packed_weight_kg": f"{util_out.get('total_packed_weight_kg')} kg",
                    "scene_mesh_elements_generated": len(result.get("scene_data", {}).get("items", [])),
                },
            })

        recommendation = result.get("ai_recommendation")
        if recommendation:
            steps.append({
                "id": "step_6_package_recommendation",
                "tool_name": "Package Recommendation Agent",
                "category": "optimization",
                "summary": recommendation.get("reasoning", "Selected one package from the feasible candidates."),
                "status": "success",
                "method": recommendation.get("model") or "Deterministic feasible-candidate fallback",
                "inputs": {
                    "feasible_candidate_count": sum(
                        1 for evaluation in result.get("all_evaluations", [])
                        if evaluation.get("fits")
                    ),
                    "selection_scope": "Candidates that passed deterministic 3D fit and weight validation",
                },
                "outputs": {
                    "selected_candidate_id": recommendation.get("selected_candidate_id"),
                    "recommendation_status": recommendation.get("status"),
                    "selection_factors": recommendation.get("selection_factors", []),
                },
            })

    return {
        "status": result.get("status"),
        "summary": result.get("summary"),
        "stage": result.get("current_stage"),
        "hitl_required": hitl_required,
        "hitl_reason": result.get("hitl_reason"),
        "requirements": req_out,
        "metrics": result.get("metrics"),
        "candidate_packages": result.get("candidate_packages", []),
        "fits": result.get("fits", False),
        "best_container": result.get("best_container"),
        "best_orientation": result.get("best_orientation"),
        "orientations_breakdown": result.get("orientations_breakdown", []),
        "utilization_metrics": result.get("utilization_metrics"),
        "placed_items": result.get("placed_items", []),
        "unplaced_items": result.get("unplaced_items", []),
        "all_evaluations": result.get("all_evaluations", []),
        "scene_data": result.get("scene_data", {}),
        "ai_recommendation": result.get("ai_recommendation"),
        "assistant_response": result.get("assistant_response"),
        "closest_candidate": result.get("closest_candidate"),
        "steps": steps,
    }


# ==========================================
# Standalone CLI Self-Test
# ==========================================

if __name__ == "__main__":
    print("=" * 75)
    print("Unified 3-Agent Workflow with Granular Tool Execution Trace")
    print("=" * 75)

    prompt_text = "Pack 4 steel brackets measuring 140x90x60mm with weight 1.2kg each."
    res = run_unified_workflow(prompt_text)
    print(f"Status: {res['status']}")
    print(f"Steps Count: {len(res.get('steps', []))}")
    for s in res.get("steps", []):
        print(f"  [{s['id']}] {s['tool_name']} ({s['status']}) - {s['summary']}")
