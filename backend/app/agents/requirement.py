import json
import logging
import time
from typing import TypedDict, Literal, Optional, Dict, Any, Union, Tuple, List
import re

from laya.integrations.langchain import LayaRouter
from langgraph.graph import START, END, StateGraph
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field, AliasChoices
from app.models import llm

try:
    from app.db import get_product_by_id, get_product_by_name, get_all_products
except Exception:
    get_product_by_id = None
    get_product_by_name = None
    get_all_products = None

logger = logging.getLogger(__name__)

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
    product_id: Optional[int] = Field(default=None, description="SQLite catalog product ID if matched")
    matched_product_id: Optional[int] = Field(default=None, description="Matched SQLite product ID")
    extra: dict = Field(default_factory=dict, description="Any additional information related to the requirement")

    model_config = {"populate_by_name": True}

    @property
    def parth_height(self) -> float:
        """Alias property for backward compatibility with 'parth_height'."""
        return self.part_height


class RequirementState(TypedDict, total=False):
    requirement: str
    check_catalog: bool
    fullfilled: bool
    fulfilled: bool
    requirements: Optional[Requirements]
    hitl_reason: Optional[str]
    laya_trace: Optional[Dict[str, Any]]
    extraction_trace: Optional[Dict[str, Any]]


REQUIREMENT_CRITERIA = {
    "yes": "Contains physical dimensions (length, width, height) to pack the item",
    "no": "Lacks dimensions, vague part description, or needs user clarification",
}

REQUIREMENT_INSTRUCTIONS = """Does this text contain explicit 3D dimensions (length, width, height or numeric dimensions like 140x90x60mm) to calculate packaging?"""


def evaluate_with_laya_details(requirements_text: str, check_catalog: bool = True) -> Dict[str, Any]:
    """Evaluate text completeness using physical geometry checks alongside LayaRouter, returning granular trace details."""
    text_lower = str(requirements_text or "").lower()

    # 1. Deterministic physical geometry validation
    has_3d_box = bool(re.search(r"\d+(?:\.\d+)?\s*[xX*×]\s*\d+(?:\.\d+)?\s*[xX*×]\s*\d+(?:\.\d+)?", text_lower))
    has_explicit_dims = bool(
        re.search(r"\blength\b", text_lower) and re.search(r"\bwidth\b", text_lower) and re.search(r"\bheight\b", text_lower)
    )
    has_catalog_ref = bool(re.search(r"\bproduct\s*(?:id)?\s*[:#]?\s*\d+\b", text_lower))

    # Also check if text matches a known product name in the database
    has_catalog_name = False
    if check_catalog and get_all_products:
        try:
            for p in get_all_products():
                pname = p.get("part_name", "").lower()
                pname_base = re.sub(r"s$", "", pname)
                if len(pname_base) >= 3 and re.search(rf"\b{re.escape(pname_base)}s?\b", text_lower):
                    has_catalog_name = True
                    break
        except Exception:
            pass

    confidence = None
    laya_choice = None
    raw_decision = None

    try:
        router = LayaRouter(
            criteria=REQUIREMENT_CRITERIA,
            instructions=REQUIREMENT_INSTRUCTIONS,
            confidence_threshold=0.5,
            fallback="no",
        )
        laya_choice = router.invoke(requirements_text)
        raw_decision = router.last_decision or {}
        ans = raw_decision.get("answers", {}).get("route", {})
        confidence = ans.get("answer_confidence") or ans.get("confidence")
    except Exception:
        laya_choice = "fallback"

    if has_3d_box or has_explicit_dims or has_catalog_ref or has_catalog_name:
        decision = "extract_requirements"
        method = "Geometric Dimension & CAD Detection"
        confidence_val = round(float(confidence * 100), 1) if confidence else 95.0
        reasoning = f"Detected physical dimensions / catalog reference. Laya semantic confidence: {confidence_val}%."
    elif laya_choice == "yes":
        decision = "extract_requirements"
        confidence_val = round(float(confidence * 100), 1) if confidence else 75.0
        reasoning = f"Laya LLM confirmed valid requirement with {confidence_val}% confidence."
        method = "Laya Semantic Classifier"
    else:
        decision = "HITL"
        confidence_val = round(float(confidence * 100), 1) if confidence else 0.0
        reasoning = "Missing required part dimensions (length, width, height) or weight specifications."
        method = "Completeness Gating"

    return {
        "decision": decision,
        "confidence": confidence_val,
        "confidence_threshold": 50.0,
        "reasoning": reasoning,
        "method": method,
        "laya_choice": laya_choice,
        "is_fulfilled": decision == "extract_requirements",
        "has_physical_dimensions": has_3d_box or has_explicit_dims or has_catalog_ref or has_catalog_name,
    }


def _evaluate_with_laya_or_fallback(text: str) -> Literal["extract_requirements", "HITL"]:
    """Fast synchronous helper for parse_requirements returning routing decision string."""
    details = evaluate_with_laya_details(text)
    return details["decision"]


def parse_requirements(
    requirements: Union[RequirementState, str]
) -> Union[Dict[str, Any], Literal["extract_requirements", "HITL"]]:
    """Parse requirement input to verify whether all required specifications are present.

    - When called with a string, returns 'extract_requirements' or 'HITL'.
    - When called as a LangGraph node with state dict, updates 'fullfilled', 'fulfilled', 'hitl_reason', and 'laya_trace'.
    """
    if isinstance(requirements, str):
        return _evaluate_with_laya_or_fallback(requirements)

    text = requirements.get("requirement", "")
    details = evaluate_with_laya_details(text, check_catalog=requirements.get("check_catalog", True))
    is_fulfilled = details["is_fulfilled"]

    return {
        "fullfilled": is_fulfilled,
        "fulfilled": is_fulfilled,
        "hitl_reason": None if is_fulfilled else details["reasoning"],
        "laya_trace": details,
    }


def route_requirements(state: RequirementState) -> Literal["extract_requirements", "HITL"]:
    """Conditional edge router: routes to 'extract_requirements' if fulfilled, else 'HITL'."""
    if state.get("fullfilled") or state.get("fulfilled"):
        return "extract_requirements"
    return "HITL"


def _extract_explicit_snp(text: str) -> Optional[int]:
    """Extract explicit quantity/SNP from text if specified, ignoring product ID numbers."""
    # Exclude "product <id>" before looking for quantity
    text_clean = re.sub(r"\bproduct\s*(?:id)?\s*[:#]?\s*\d+\b", "", text, flags=re.IGNORECASE)

    # 1. snp = 64, quantity: 64, qty = 64
    m = re.search(r"\b(?:snp|quantity|qty|count)\s*[:=]?\s*(\d+)\b", text_clean, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 2. "pack 64 units", "shipping for 50", "package for 4"
    m = re.search(r"(?:pack|packaging for|packing for|package for|packages for|carton for|box for|shipping for)\s+(\d+)\b", text_clean, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # 3. "64 units", "64 parts", "64 pieces", "64 items"
    m = re.search(r"\b(\d+)\s+(?:(?:[a-zA-Z]+)\s+)?(?:units|parts|pieces|items|brackets|pins|doors|plates|boxes|housings|bushings|assemblies|modules|heatsinks|clips|ingots|sensors)\b", text_clean, re.IGNORECASE)
    if m:
        return int(m.group(1))

    return None


def _match_catalog_product(text: str) -> Optional[Tuple[Dict[str, Any], Optional[int]]]:
    """Check if the text references a catalog product by ID or by name from SQLite products table.

    Returns:
        (product_dict, explicit_snp_if_any) or None
    """
    text_lower = text.lower()

    # 1. Check for explicit product ID: e.g. "product 1", "product id: 1", "product #1", "lookup product 1"
    pid_match = re.search(r"\bproduct\s*(?:id)?\s*[:#]?\s*(\d+)\b", text_lower)
    if pid_match and get_product_by_id:
        try:
            pid = int(pid_match.group(1))
            prod = get_product_by_id(pid)
            if prod:
                explicit_snp = _extract_explicit_snp(text)
                return prod, explicit_snp
        except Exception:
            pass

    # 2. Check for catalog product names (e.g. "Micro Terminal Block")
    if get_all_products:
        try:
            all_prods = get_all_products()
            for prod in sorted(all_prods, key=lambda p: len(p.get("part_name", "")), reverse=True):
                pname = prod.get("part_name", "")
                pname_base = re.sub(r"s$", "", pname, flags=re.IGNORECASE)
                if len(pname_base) >= 3 and re.search(rf"\b{re.escape(pname_base)}s?\b", text, re.IGNORECASE):
                    explicit_snp = _extract_explicit_snp(text)
                    return prod, explicit_snp
        except Exception:
            pass

    return None


def _fallback_extract(text: str, check_catalog: bool = True) -> Requirements:
    """Fallback extractor: checks SQLite catalog first, then deterministic regex extraction."""
    # 0. Check SQLite catalog match first
    catalog_match = _match_catalog_product(text) if check_catalog else None
    if catalog_match:
        prod, explicit_snp = catalog_match
        pid = prod.get("id")
        snp_val = explicit_snp or prod.get("standard_no_of_parts") or 1
        return Requirements(
            name=str(prod.get("part_name", f"Product {pid}")),
            description=text.strip() or f"Catalog Product {pid}",
            snp=str(snp_val),
            part_length=float(prod.get("part_length", 100.0)),
            part_width=float(prod.get("part_breadth", prod.get("part_width", 80.0))),
            part_height=float(prod.get("part_height", 50.0)),
            part_type=str(prod.get("part_type", "Standard")),
            part_weight=float(prod.get("part_weight", 1.0)),
            product_id=pid,
            matched_product_id=pid,
            extra={"product_id": pid, "matched_product_id": pid, "catalog_matched": True},
        )

    def _search_num(pattern: str, default: float) -> float:
        m = re.search(pattern, text, re.IGNORECASE)
        return float(m.group(1)) if m else default

    # Exclude product ID mentions before extracting raw numbers
    text_clean = re.sub(r"\bproduct\s*(?:id)?\s*[:#]?\s*\d+\b", "", text, flags=re.IGNORECASE)

    # 1. 3D Dimensions: Check for compact 3D dimension box (e.g., 140x90x60mm or 140 x 90 x 60 mm)
    dim_box = re.search(r"(\d+(?:\.\d+)?)\s*[xX*×]\s*(\d+(?:\.\d+)?)\s*[xX*×]\s*(\d+(?:\.\d+)?)", text)
    if dim_box:
        length = float(dim_box.group(1))
        width = float(dim_box.group(2))
        height = float(dim_box.group(3))
    else:
        nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text_clean)]
        length = _search_num(r"length\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[0] if len(nums) > 0 else 100.0)
        width = _search_num(r"width\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[1] if len(nums) > 1 else 100.0)
        height = _search_num(r"height\s*[:=]?\s*(\d+(?:\.\d+)?)", nums[2] if len(nums) > 2 else 50.0)

    # 2. Weight
    weight = _search_num(r"weight\s*[:=]?\s*(\d+(?:\.\d+)?)", 0.0)
    if weight == 0.0:
        wt_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilos?|kilograms?|lbs?)\b", text, re.IGNORECASE)
        weight = float(wt_m.group(1)) if wt_m else 1.0

    # 3. Material
    mat_match = re.search(r"\b(steel|aluminum|plastic|glass|metal|brass|iron|wood|rubber|ceramic|copper)\b", text, re.IGNORECASE)
    part_type = mat_match.group(1).lower() if mat_match else "standard"

    # 4. SNP / Quantity
    explicit_snp = _extract_explicit_snp(text)
    snp = str(explicit_snp) if explicit_snp is not None else "SNP-1"

    # 5. Name
    name_match = re.search(r"(?:part|name)\s*[:=]?\s*([a-zA-Z0-9_\- ]+?)(?=\s+(?:length|width|height|weight|material|type|snp|$))", text, re.IGNORECASE)
    if not name_match:
        name_match = re.search(r"(?:for|pack)\s+(?:\d+\s+)?([a-zA-Z0-9_\- ]+?)(?=\s+(?:measuring|with|having|dimensions|length|width|height|weight|material|type|$))", text, re.IGNORECASE)
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


class GatheredItem(BaseModel):
    """One item mentioned in the active packaging task; fields may arrive over several turns."""
    name: Optional[str] = None
    product_id: Optional[int] = None
    catalog_reference: bool = Field(default=False, description="True when the user intends this to be a catalog product lookup")
    quantity: Optional[int] = Field(default=None, ge=1)
    part_length: Optional[float] = Field(default=None, gt=0)
    part_width: Optional[float] = Field(default=None, gt=0)
    part_height: Optional[float] = Field(default=None, gt=0)
    part_weight: Optional[float] = Field(default=None, gt=0)
    part_type: Optional[str] = None
    description: Optional[str] = None


class RequirementTurnExtraction(BaseModel):
    """Structured outcome of one conversational requirement-gathering turn."""
    items: List[GatheredItem] = Field(default_factory=list)
    assistant_message: str = Field(description="A concise natural follow-up or acknowledgment for the user")


def _explicit_catalog_items(message: str) -> List[GatheredItem]:
    # Common typing errors include "prouduct" and transposed "proudct".
    refs = list(re.finditer(r"\bpr(?:o|ou)(?:d?u?ct|udct)\s*(?:id)?\s*[:#]?\s*(\d+)\b", message, re.IGNORECASE))
    items: List[GatheredItem] = []
    for index, ref in enumerate(refs):
        product_id = int(ref.group(1))
        previous_end = refs[index - 1].end() if index else 0
        next_start = refs[index + 1].start() if index + 1 < len(refs) else len(message)
        before = message[previous_end:ref.start()]
        after = message[ref.end():next_start]
        quantity_match = re.search(
            r"(\d+)\s*(?:units?|pieces?|parts?|items?)?\s*(?:of|for)?\s*$",
            before,
            re.IGNORECASE,
        )
        if not quantity_match:
            quantity_match = re.match(r"\s*(?:x|\u00d7|:)?\s*(\d+)\b", after, re.IGNORECASE)
        product = get_product_by_id(product_id) if get_product_by_id else None
        items.append(GatheredItem(
            name=product.get("part_name") if product else f"Product {product_id}",
            product_id=product_id,
            catalog_reference=True,
            quantity=int(quantity_match.group(1)) if quantity_match else None,
        ))
    return items


def _fallback_requirement_turn(
    message: str,
    draft_items: List[Dict[str, Any]],
) -> RequirementTurnExtraction:
    """Conservative extraction fallback used only when the configured LLM call fails."""
    explicit_items = _explicit_catalog_items(message)
    if explicit_items:
        return RequirementTurnExtraction(
            items=explicit_items,
            assistant_message="I found product references. I’ll check each one in the catalog and show you the matches to confirm.",
        )

    return RequirementTurnExtraction(
        items=[],
        assistant_message="Which product name or product ID from the catalog would you like to pack?",
    )


def gather_requirements_turn(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    accumulated_manifest: Optional[List[Dict[str, Any]]] = None,
    draft_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Call the LLM on every gathering turn and return updated active item drafts."""
    history_text = "\n".join(
        f"{turn.get('role', 'user')}: {turn.get('content', '')}"
        for turn in (conversation_history or [])[-12:]
    )
    prompt = (
        "You are a conversational assistant that gathers catalog product choices for a packaging task. Analyze the newest "
        "message together with prior conversation and the confirmed manifest. Return every newly mentioned catalog product "
        "with its quantity. Never repeat or alter committed manifest items. Never invent product IDs, quantities, or facts. "
        "Set catalog_reference=true only when the user intends a specific product from the database (by product ID, SKU, "
        "or unambiguous catalog name). Generic discussion, custom products, dimensions, and ordinary conversation are not "
        "optimization items; respond conversationally and ask which database product they mean when appropriate. "
        "When a catalog item is identified, say it will be checked and shown for confirmation.\n\n"
        f"Committed manifest (read only): {json.dumps(accumulated_manifest or [], ensure_ascii=False)}\n"
        f"Active draft items: {json.dumps(draft_items or [], ensure_ascii=False)}\n"
        f"Recent conversation:\n{history_text}\n"
        f"Newest user message: {message}\n"
        "Return the updated active/new items only and one concise assistant reply."
    )
    try:
        started = time.perf_counter()
        logger.info("llm.call.started operation=requirement_extraction")
        extractor = llm.with_structured_output(RequirementTurnExtraction)
        extracted = extractor.invoke(prompt)
        logger.info("llm.call.completed operation=requirement_extraction duration_ms=%.2f", (time.perf_counter() - started) * 1000)
        if isinstance(extracted, dict):
            extracted = RequirementTurnExtraction.model_validate(extracted)
        explicit_items = _explicit_catalog_items(message)
        if explicit_items:
            extracted.items = [item for item in extracted.items if item.product_id is None] + explicit_items
        if not extracted.assistant_message.strip():
            extracted.assistant_message = "What else should I know about the part?"
        return {
            "items": [item.model_dump(exclude_none=True) for item in extracted.items],
            "assistant_message": extracted.assistant_message,
            "method": "Azure OpenAI Conversational Requirement Extractor",
            "status": "llm_extracted",
        }
    except Exception:
        logger.exception("llm.call.failed operation=requirement_extraction")
        fallback = _fallback_requirement_turn(message, draft_items or [])
        return {
            "items": [item.model_dump(exclude_none=True) for item in fallback.items],
            "assistant_message": fallback.assistant_message,
            "method": "Conservative Deterministic Fallback",
            "status": "llm_unavailable_fallback",
        }


def generate_conversation_prompt(
    purpose: str,
    manifest: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Ask the configured LLM to phrase a short next-step question for the user."""
    fallback = {
        "ask_add_more": "Would you like to add another product or part to this optimization task?",
        "ask_next_item": "What product or part would you like to add next?",
    }.get(purpose, "What would you like to do next?")
    prompt = (
        "Write one brief, natural chatbot message for a packaging workflow. Do not invent facts or requirements. "
        f"The required conversational action is: {purpose}. The confirmed task manifest is "
        f"{json.dumps(manifest or [], ensure_ascii=False)}. Recent conversation: "
        f"{json.dumps((conversation_history or [])[-8:], ensure_ascii=False)}. Return only the message."
    )
    try:
        started = time.perf_counter()
        logger.info("llm.call.started operation=conversation_prompt purpose=%s", purpose)
        response = llm.invoke(prompt)
        logger.info("llm.call.completed operation=conversation_prompt purpose=%s duration_ms=%.2f", purpose, (time.perf_counter() - started) * 1000)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = " ".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
        message = str(content).strip().strip('"')
        return message or fallback
    except Exception:
        logger.exception("llm.call.failed operation=conversation_prompt purpose=%s", purpose)
        return fallback


def extract_requirements(
    requirements: Union[RequirementState, str]
) -> Union[Requirements, Dict[str, Any]]:
    """Extract structured Requirements from input text using catalog auto-lookup, LLM structured output, or deterministic fallback.

    - When called with a string, returns a Requirements model instance.
    - When called as a LangGraph node with state dict, updates 'requirements' and 'extraction_trace' in state.
    """
    if isinstance(requirements, str):
        req_text = requirements
        check_catalog = True
    else:
        req_text = requirements.get("requirement", "")
        check_catalog = requirements.get("check_catalog", True)

    # 1. Priority A: Check if input references a catalog product from SQLite database
    catalog_match = _match_catalog_product(req_text) if check_catalog else None
    if catalog_match:
        prod, explicit_snp = catalog_match
        pid = prod.get("id")
        snp_val = explicit_snp or prod.get("standard_no_of_parts") or 1
        res = Requirements(
            name=str(prod.get("part_name", f"Product {pid}")),
            description=req_text.strip() or f"Catalog Product {pid}",
            snp=str(snp_val),
            part_length=float(prod.get("part_length", 100.0)),
            part_width=float(prod.get("part_breadth", prod.get("part_width", 80.0))),
            part_height=float(prod.get("part_height", 50.0)),
            part_type=str(prod.get("part_type", "Standard")),
            part_weight=float(prod.get("part_weight", 1.0)),
            product_id=pid,
            matched_product_id=pid,
            extra={"product_id": pid, "matched_product_id": pid, "catalog_matched": True},
        )
        extraction_method = "SQLite Catalog Auto-Lookup (Products Table)"
        extraction_status = f"database_catalog_matched (Product ID: {pid})"
    else:
        # 2. Priority B: Ad-hoc custom part - Extract via LLM or deterministic fallback
        prompt = PromptTemplate.from_template(
            "Extract the packing and part requirements from the following text: {requirements}"
        )
        extraction_method = "Azure OpenAI (gpt-4o)"
        extraction_status = "live_llm"

        try:
            llm_with_structured_output = llm.with_structured_output(Requirements)
            res = llm_with_structured_output.invoke(prompt.format(requirements=req_text))
        except Exception:
            res = _fallback_extract(req_text, check_catalog=check_catalog)
            extraction_method = "Deterministic Regex Extractor"
            extraction_status = "fallback_rules (LLM credentials placeholder)"

    if isinstance(requirements, str):
        return res

    extraction_trace = {
        "method": extraction_method,
        "status": extraction_status,
        "parameters_extracted": res.model_dump(),
        "input_prompt": req_text,
    }

    return {
        "requirements": res,
        "fullfilled": True,
        "fulfilled": True,
        "extraction_trace": extraction_trace,
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
