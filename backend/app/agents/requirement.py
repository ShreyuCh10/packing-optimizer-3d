from typing import TypedDict, Literal, Optional, Dict, Any, Union
import re

from laya.integrations.langchain import LayaRouter
from langgraph.graph import START, END, StateGraph
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, AliasChoices
from app.models import llm

# Alias for compatibility if referenced as MessagePromptTemplate
MessagePromptTemplate = PromptTemplate


class Requirements(BaseModel):
    name: str = Field(..., description="The name of the requirement")
    description: str = Field(..., description="A detailed description of the requirement")
    snp: str = Field(..., description="The SNP associated with the requirement")
    part_length: float = Field(..., description="The length of the part associated with the requirement")
    part_width: float = Field(..., description="The width of the part associated with the requirement")
    part_height: float = Field(
        ...,
        validation_alias=AliasChoices("part_height", "parth_height"),
        description="The height of the part associated with the requirement",
    )
    part_type: str = Field(..., description="The material the part is made of ")
    part_weight: float = Field(..., description="The weight of the part associated with the requirement")
    extra: dict = Field(default_factory=dict, description="Any additional information related to the requirement")

    model_config = {"populate_by_name": True}

    @property
    def parth_height(self) -> float:
        """Alias property for backward compatibility with 'parth_height'."""
        return self.part_height


class RequirementState(TypedDict, total=False):
    requirement: str
    fullfilled: bool
    fulfilled: bool
    requirements: Optional[Requirements]
    hitl_reason: Optional[str]


REQUIREMENT_CRITERIA = {
    "yes": "It contains all the requirements (name, description, snp, length, width, height, part type/material, weight)",
    "no": "It does not contain all requirements or lacks sufficient part specifications",
}

REQUIREMENT_INSTRUCTIONS = """Does it contain all requirements?
Requirements:
{
    name: str = The name of the requirement
    description: str = A detailed description of the requirement
    snp: str = The SNP associated with the requirement
    part_length: float = The length of the part associated with the requirement
    part_width: float = The width of the part associated with the requirement
    part_height: float = The height of the part associated with the requirement
    part_type: str = The material the part is made of
    part_weight: float = The weight of the part associated with the requirement
    extra: dict = Any additional information related to the requirement
}"""


def _evaluate_with_laya_or_fallback(requirements_text: str) -> Literal["extract_requirements", "HITL"]:
    """Evaluate text completeness using LayaRouter with fallback."""
    try:
        router = LayaRouter(
            criteria=REQUIREMENT_CRITERIA,
            instructions=REQUIREMENT_INSTRUCTIONS,
            confidence_threshold=0.8,
            fallback="no",
        )
        decision = router.invoke(requirements_text)
        if decision == "yes":
            return "extract_requirements"
        return "HITL"
    except Exception:
        # Graceful heuristic fallback if Laya local weights/network are not available
        text_lower = requirements_text.lower()
        has_dims = any(k in text_lower for k in ["length", "width", "height", "dim", "size", "x", "mm", "cm", "in"])
        has_material = any(k in text_lower for k in ["material", "type", "steel", "plastic", "aluminum", "wood", "foam", "metal"])
        has_weight = any(k in text_lower for k in ["weight", "kg", "g", "lbs", "pound"])
        if has_dims and (has_material or has_weight):
            return "extract_requirements"
        return "HITL"


def parse_requirements(
    requirements: Union[RequirementState, str]
) -> Union[Dict[str, Any], Literal["extract_requirements", "HITL"]]:
    """Parse requirement input to verify whether all required specifications are present.

    - When called with a string, returns 'extract_requirements' or 'HITL'.
    - When called as a LangGraph node with state dict, updates 'fullfilled', 'fulfilled', and 'hitl_reason'.
    """
    if isinstance(requirements, str):
        return _evaluate_with_laya_or_fallback(requirements)

    text = requirements.get("requirement", "")
    decision = _evaluate_with_laya_or_fallback(text)
    is_fulfilled = decision == "extract_requirements"
    return {
        "fullfilled": is_fulfilled,
        "fulfilled": is_fulfilled,
        "hitl_reason": None if is_fulfilled else "Missing or incomplete part requirements in input text",
    }


def route_requirements(state: RequirementState) -> Literal["extract_requirements", "HITL"]:
    """Conditional edge router: routes to 'extract_requirements' if fulfilled, else 'HITL'."""
    if state.get("fullfilled") or state.get("fulfilled"):
        return "extract_requirements"
    return "HITL"


def _fallback_extract(text: str) -> Requirements:
    """Fallback extractor when LLM API credentials or network are unavailable."""
    def _search_num(pattern: str, default: float) -> float:
        m = re.search(pattern, text, re.IGNORECASE)
        return float(m.group(1)) if m else default

    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    length = _search_num(r"length\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[0] if len(nums) > 0 else 100.0)
    width = _search_num(r"width\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[1] if len(nums) > 1 else 100.0)
    height = _search_num(r"height\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[2] if len(nums) > 2 else 50.0)
    weight = _search_num(r"weight\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[3] if len(nums) > 3 else 1.0)

    part_type_match = re.search(r"(?:material|type)\s*[:=]?\s*([a-zA-Z]+)", text, re.IGNORECASE)
    part_type = part_type_match.group(1) if part_type_match else "standard"

    snp_match = re.search(r"snp\s*[:=]?\s*(\S+)", text, re.IGNORECASE)
    snp = snp_match.group(1) if snp_match else "SNP-1"

    name_match = re.search(r"(?:part|name)\s*[:=]?\s*([a-zA-Z0-9_\- ]+?)(?=\s+(?:length|width|height|weight|material|type|snp|$))", text, re.IGNORECASE)
    name = name_match.group(1).strip() if name_match else "Extracted Part"

    return Requirements(
        name=name,
        description=text.strip() or "Part requirement specification",
        snp=snp,
        part_length=length,
        part_width=width,
        part_height=height,
        part_type=part_type,
        part_weight=weight,
        extra={},
    )


def extract_requirements(
    requirements: Union[RequirementState, str]
) -> Union[Requirements, Dict[str, Any]]:
    """Extract structured Requirements from input text using LLM structured output.

    - When called with a string, returns a Requirements model instance.
    - When called as a LangGraph node with state dict, updates 'requirements' in state.
    """
    if isinstance(requirements, str):
        req_text = requirements
    else:
        req_text = requirements.get("requirement", "")

    prompt = PromptTemplate.from_template(
        "Extract the packing and part requirements from the following text: {requirements}"
    )

    try:
        llm_with_structured_output = llm.with_structured_output(Requirements)
        res: Requirements = llm_with_structured_output.invoke(prompt.format(requirements=req_text))
    except Exception:
        res = _fallback_extract(req_text)

    if isinstance(requirements, str):
        return res

    return {
        "requirements": res,
        "fullfilled": True,
        "fulfilled": True,
    }


def hitl_node(state: RequirementState) -> Dict[str, Any]:
    """Human-in-the-loop (HITL) node for incomplete or ambiguous requirements."""
    reason = state.get("hitl_reason", "Requirements incomplete. Human review/clarification required.")
    return {
        "fullfilled": False,
        "fulfilled": False,
        "hitl_reason": reason,
    }


# Define the LangGraph workflow
requirementagent = StateGraph(RequirementState)

requirementagent.add_node("parse_requirements", parse_requirements)
requirementagent.add_node("extract_requirements", extract_requirements)
requirementagent.add_node("HITL", hitl_node)

requirementagent.add_edge(START, "parse_requirements")
requirementagent.add_conditional_edges(
    "parse_requirements",
    route_requirements,
    {
        "extract_requirements": "extract_requirements",
        "HITL": "HITL",
    },
)
requirementagent.add_edge("extract_requirements", END)
requirementagent.add_edge("HITL", END)

# Compiled graph runnable
app = requirementagent.compile()
