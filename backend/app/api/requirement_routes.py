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
