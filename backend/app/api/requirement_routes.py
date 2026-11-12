from typing import Optional, Dict, Any
from uuid import uuid4
import json
import logging
import queue
import threading
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

from app.agents.requirement import (
    app as requirement_app,
    parse_requirements,
    extract_requirements,
    Requirements,
    RequirementState,
)

router = APIRouter(prefix="/requirements", tags=["Requirements Agent"])
logger = logging.getLogger(__name__)


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
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
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
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval agent failed: {str(e)}")


class OKFDecisionInput(BaseModel):
    user_query: str = Field(..., min_length=1, description="Question to answer from the local OKF packaging knowledge documents")


@router.post("/okf/decide", summary="Make an evidence-based decision from OKF packaging guidance")
def decide_from_okf(input_data: OKFDecisionInput):
    """Run the bounded LangGraph workflow over local OKF Markdown sources."""
    from app.agents.okf_workflow import run_okf_decision
    try:
        return run_okf_decision(input_data.user_query.strip())
    except Exception as exc:
        logger.exception("api.okf_decision.failed")
        raise HTTPException(status_code=500, detail=f"OKF decision workflow failed: {exc}")


def _run_chat_turn(input_data: Dict[str, Any], on_stage=None, owner_id: str = "local") -> Dict[str, Any]:
    from app.agents.conversation_workflow import process_chat_turn
    user_in = input_data.get("user_input", input_data)
    conversation_id = str(input_data.get("conversation_id") or uuid4())
    return process_chat_turn(
        conversation_id=conversation_id,
        user_input=user_in,
        owner_id=owner_id,
        allow_rotation=input_data.get("allow_rotation", True),
        keep_upright=input_data.get("keep_upright", False),
        max_candidate_packages=input_data.get("max_candidate_packages", 5),
        on_stage=on_stage,
    )


@router.post("/workflow/stream", summary="Run stateful packaging workflow with live stage updates")
def run_workflow_stream_endpoint(input_data: Dict[str, Any], request: Request = None):
    """Stream actual backend stage changes followed by the completed workflow result."""
    events: queue.Queue = queue.Queue()

    def execute():
        started = time.perf_counter()
        try:
            result = _run_chat_turn(
                input_data,
                on_stage=lambda label: events.put({"type": "progress", "label": label}),
                owner_id=getattr(getattr(request, "state", None), "authenticated_user_id", "local"),
            )
            events.put({"type": "result", "result": result})
            logger.info("api.workflow.completed conversation_id=%s duration_ms=%.2f", result.get("conversation_id"), (time.perf_counter() - started) * 1000)
        except Exception as exc:
            logger.exception("api.workflow.failed duration_ms=%.2f", (time.perf_counter() - started) * 1000)
            events.put({"type": "error", "message": str(exc)})
        finally:
            events.put(None)

    def event_stream():
        worker = threading.Thread(target=execute, daemon=True)
        worker.start()
        while True:
            event = events.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/workflow/execute", summary="Run a catalog-validated structured packing manifest")
def execute_workflow_endpoint(input_data: Dict[str, Any]):
    """Run an already selected cart manifest through catalog validation and full optimization."""
    started = time.perf_counter()
    user_input = input_data.get("user_input", input_data)
    if not isinstance(user_input, dict) or not isinstance(user_input.get("items"), list) or not user_input["items"]:
        raise HTTPException(status_code=400, detail="A non-empty cart product manifest is required.")
    try:
        from app.agents.workflow import run_unified_workflow

        result = run_unified_workflow(
            user_input,
            allow_rotation=input_data.get("allow_rotation", True),
            keep_upright=input_data.get("keep_upright", False),
            max_candidate_packages=input_data.get("max_candidate_packages", 5),
        )
        requirement_items = (result.get("requirements") or {}).get("items") or []
        result["task_manifest"] = [
            {
                "product_id": item.get("product_id") or item.get("matched_product_id"),
                "part_name": item.get("part_name") or item.get("name"),
                "name": item.get("part_name") or item.get("name"),
                "quantity": int(item.get("quantity") or item.get("number_of_parts") or item.get("snp") or 1),
            }
            for item in requirement_items
        ] or [
            {
                "product_id": item.get("product_id"),
                "part_name": item.get("part_name") or item.get("name"),
                "name": item.get("part_name") or item.get("name"),
                "quantity": int(item.get("number_of_parts") or item.get("quantity") or item.get("snp") or 1),
            }
            for item in user_input["items"]
        ]
        if result.get("stage") == "packing_optimization":
            result["action"] = "optimized"
        logger.info("api.workflow.execute.completed item_count=%d duration_ms=%.2f", len(user_input["items"]), (time.perf_counter() - started) * 1000)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("api.workflow.execute.failed duration_ms=%.2f", (time.perf_counter() - started) * 1000)
        raise HTTPException(status_code=500, detail=f"Cart optimization workflow failed: {str(exc)}")


@router.post("/workflow", summary="Run End-to-End 3-Agent Packaging Workflow")
def run_workflow_endpoint(input_data: Dict[str, Any], request: Request = None):
    """Process a stateful chat turn, then optimize after the user finishes adding requirements."""
    started = time.perf_counter()
    try:
        result = _run_chat_turn(
            input_data,
            owner_id=getattr(getattr(request, "state", None), "authenticated_user_id", "local"),
        )
        logger.info("api.workflow.completed conversation_id=%s duration_ms=%.2f", result.get("conversation_id"), (time.perf_counter() - started) * 1000)
        return result
    except PermissionError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except Exception as e:
        logger.exception("api.workflow.failed duration_ms=%.2f", (time.perf_counter() - started) * 1000)
        raise HTTPException(status_code=500, detail=f"Unified workflow failed: {str(e)}")
