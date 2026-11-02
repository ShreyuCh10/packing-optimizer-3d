from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.requirement import (
    app as requirement_app,
    parse_requirements,
    extract_requirements,
    Requirements,
    RequirementState,
)

router = APIRouter(prefix="/requirements", tags=["Requirements Agent"])


class RequirementInput(BaseModel):
    requirement: str = Field(..., description="Unstructured text containing part or packaging requirements")


class RequirementAnalysisResponse(BaseModel):
    requirement: str
    fullfilled: bool
    requirements: Optional[Requirements] = None
    hitl_reason: Optional[str] = None


class HITLResolveInput(BaseModel):
    original_requirement: str = Field(..., description="The original requirement text")
    additional_info: str = Field(..., description="Additional clarifications or missing dimensions provided by human")


@router.post("/analyze", response_model=RequirementAnalysisResponse, summary="Analyze requirement text via Agent workflow")
def analyze_requirement(input_data: RequirementInput):
    """Run the LangGraph requirement agent workflow to parse and extract part requirements."""
    try:
        initial_state: RequirementState = {"requirement": input_data.requirement}
        result = requirement_app.invoke(initial_state)

        return RequirementAnalysisResponse(
            requirement=result.get("requirement", input_data.requirement),
            fullfilled=bool(result.get("fullfilled") or result.get("fulfilled")),
            requirements=result.get("requirements"),
            hitl_reason=result.get("hitl_reason"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Requirement agent failed: {str(e)}")


@router.post("/parse", summary="Check requirement completeness with LayaRouter")
def parse_requirement_completeness(input_data: RequirementInput):
    """Check if the text contains all necessary part requirements before extraction."""
    try:
        decision = parse_requirements(input_data.requirement)
        is_ready = decision == "extract_requirements"
        return {
            "requirement": input_data.requirement,
            "decision": decision,
            "is_complete": is_ready,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract", response_model=Requirements, summary="Directly extract structured Requirements")
def extract_structured_requirements(input_data: RequirementInput):
    """Extract structured Requirements schema using LLM structured output."""
    try:
        res = extract_requirements(input_data.requirement)
        if isinstance(res, dict):
            req_obj = res.get("requirements")
            if req_obj is None:
                raise HTTPException(status_code=422, detail="Failed to extract requirements from text")
            return req_obj
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/hitl/resolve", response_model=RequirementAnalysisResponse, summary="Resolve HITL by supplying missing information")
def resolve_hitl_clarification(input_data: HITLResolveInput):
    """Combine original requirement with additional human clarification and re-run agent."""
    combined_text = f"{input_data.original_requirement.strip()}. Additional details: {input_data.additional_info.strip()}"
    try:
        result = requirement_app.invoke({"requirement": combined_text})
        return RequirementAnalysisResponse(
            requirement=combined_text,
            fullfilled=bool(result.get("fullfilled") or result.get("fulfilled")),
            requirements=result.get("requirements"),
            hitl_reason=result.get("hitl_reason"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HITL resolution failed: {str(e)}")


class RetrievalInput(BaseModel):
    product_id: Optional[int] = Field(default=None, description="Optional SQLite Product ID to auto-load attributes")
    name: Optional[str] = Field(default=None, description="Part name")
    part_length: Optional[float] = Field(default=None, description="Part length in mm")
    part_width: Optional[float] = Field(default=None, description="Part width in mm")
    part_height: Optional[float] = Field(default=None, description="Part height in mm")
    part_weight: Optional[float] = Field(default=None, description="Part weight in kg")
    part_type: Optional[str] = Field(default=None, description="Material type")
    snp: Optional[Any] = Field(default=None, description="Standard Number of Packs (SNP)")
    max_results: Optional[int] = Field(default=5, ge=1, le=20, description="Max packages to return")


@router.post("/retrieve", summary="Run Retrieval & Gathering Agent to narrow down useful packages from SQLite")
def retrieve_packages(input_data: RetrievalInput):
    """Deterministically calculate physical metrics and query SQLite database tables to narrow down useful packages."""
    from app.agents.retrieval_gathering import run_retrieval_gathering
    try:
        data = input_data.model_dump()
        max_res = int(data.pop("max_results", 5) or 5)
        return run_retrieval_gathering(data, max_results=max_res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval agent failed: {str(e)}")


@router.post("/workflow", summary="Run End-to-End 3-Agent Packaging Workflow")
def run_workflow_endpoint(input_data: Dict[str, Any]):
    """Execute the full 3-Agent pipeline: Requirement Gathering -> Retrieval & Gathering -> 3D Packing Optimization."""
    from app.agents.workflow import run_unified_workflow
    try:
        user_in = input_data.get("user_input", input_data)
        allow_rot = input_data.get("allow_rotation", True)
        keep_up = input_data.get("keep_upright", False)
        max_c = input_data.get("max_candidate_packages", 5)
        return run_unified_workflow(
            user_input=user_in,
            allow_rotation=allow_rot,
            keep_upright=keep_up,
            max_candidate_packages=max_c,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unified workflow failed: {str(e)}")
