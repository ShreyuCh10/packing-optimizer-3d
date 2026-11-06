"""Multi-turn requirement gathering and packaging task orchestration."""

import re
import logging
import math
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from app.agents.requirement import gather_requirements_turn, generate_conversation_prompt
from app.services.conversation_store import load_conversation, save_conversation
from app.db import get_product_by_id, get_product_by_name, get_all_products

logger = logging.getLogger(__name__)


def _new_state() -> Dict[str, Any]:
    return {
        "phase": "gathering",
        "history": [],
        "manifest": [],
        "draft_items": [],
        "pending_products": [],
    }


def _reply(
    conversation_id: str,
    state: Dict[str, Any],
    message: str,
    *,
    extraction_method: Optional[str] = None,
    status: str = "conversation_gathering",
) -> Dict[str, Any]:
    state["history"].append({"role": "assistant", "content": message})
    state["history"] = state["history"][-50:]
    save_conversation(conversation_id, state)
    response = {
        "status": status,
        "stage": "requirement_gathering",
        "action": "conversation",
        "conversation_id": conversation_id,
        "summary": message,
        "assistant_response": message,
        "hitl_required": False,
        "confirmation_required": False,
        "product_not_found": False,
        "fits": False,
        "task_manifest": state.get("manifest", []),
        "draft_items": state.get("draft_items", []),
    }
    if extraction_method:
        response["extraction_method"] = extraction_method
    return response


def _catalog_item(row: Dict[str, Any], quantity: Optional[int]) -> Dict[str, Any]:
    dimensions = [row.get("part_length"), row.get("part_breadth"), row.get("part_height")]
    try:
        dimensions = [float(value) for value in dimensions]
        weight = float(row.get("part_weight"))
    except (TypeError, ValueError):
        raise ValueError("Catalog product is missing valid dimensions or weight")
    if any(not math.isfinite(value) or value <= 0 for value in dimensions) or not math.isfinite(weight) or weight < 0:
        raise ValueError("Catalog product dimensions must be positive and weight cannot be negative")
    return {
        "product_id": row["id"],
        "part_name": row["part_name"],
        "name": row["part_name"],
        "part_length": dimensions[0],
        "part_width": dimensions[1],
        "part_height": dimensions[2],
        "part_weight": weight,
        "part_type": row.get("part_type", "Standard"),
        "quantity": max(1, int(quantity or row.get("standard_no_of_parts") or 1)),
    }


def _is_yes(text: str) -> bool:
    return bool(re.search(
        r"\b(?:yes|yeah|yep|sure|okay|ok|add another|another (?:product|item)|one more|more)\b",
        text,
        re.IGNORECASE,
    ))


def _is_no(text: str) -> bool:
    return bool(re.match(
        r"^\s*(?:no|nope|done|finished|complete|proceed|that's all|that is all|all set|nothing else|"
        r"optimize|optimise|start packing|start optimization|start optimisation)\b",
        text,
        re.IGNORECASE,
    ))


def _manifest_confirmation_response(
    conversation_id: str,
    state: Dict[str, Any],
    extraction_method: Optional[str] = None,
) -> Dict[str, Any]:
    products = state.get("pending_products", [])
    total_quantity = sum(int(item.get("quantity", 1)) for item in products)
    message = (
        f"I found {len(products)} product(s) in the catalog, {total_quantity} units total. "
        "Please review this list and confirm before I add it to the optimization task."
    )
    state["phase"] = "awaiting_catalog_confirmation"
    state["history"].append({"role": "assistant", "content": message})
    state["history"] = state["history"][-50:]
    save_conversation(conversation_id, state)
    response: Dict[str, Any] = {
        "status": "awaiting_confirmation",
        "stage": "requirement_gathering",
        "action": "confirm_product",
        "conversation_id": conversation_id,
        "summary": message,
        "assistant_response": message,
        "hitl_required": False,
        "confirmation_required": True,
        "product_not_found": False,
        "fits": False,
        "requested_quantity": total_quantity,
        "matched_products": products,
        "task_manifest": state.get("manifest", []),
    }
    if len(products) == 1:
        product = products[0]
        response["matched_product"] = {
            "id": product["product_id"],
            "part_name": product["part_name"],
            "part_length": product["part_length"],
            "part_breadth": product["part_width"],
            "part_height": product["part_height"],
            "part_weight": product["part_weight"],
            "part_type": product.get("part_type"),
            "standard_no_of_parts": product["quantity"],
        }
    if extraction_method:
        response["extraction_method"] = extraction_method
    return response


def _unknown_catalog_response(conversation_id: str, state: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    identifier = f"Product ID #{item['product_id']}" if item.get("product_id") else f"'{item.get('name', 'that product')}'"
    message = (
        f"I couldn't find {identifier} in the product catalog. Could you check the product name or ID? "
        "This optimization can only include products that are already in the catalog."
    )
    response = _reply(conversation_id, state, message, status="product_not_found")
    response.update({
        "product_not_found": True,
        "hitl_required": True,
        "hitl_reason": message,
    })
    name = str(item.get("name") or "").strip()
    if name and item.get("product_id") is None:
        normalized = lambda value: re.sub(r"[^a-z0-9]+", "", str(value).lower())
        target = normalized(name)
        try:
            ranked = sorted(
                (
                    (SequenceMatcher(None, target, normalized(row.get("part_name", ""))).ratio(), row)
                    for row in get_all_products()
                ),
                key=lambda pair: pair[0],
                reverse=True,
            )
            suggestions = [
                {"product_id": row["id"], "part_name": row["part_name"], "similarity": round(score, 3)}
                for score, row in ranked[:3]
                if score >= 0.45
            ]
            if suggestions:
                response["catalog_suggestions"] = suggestions
                response["assistant_response"] += " Possible catalog matches: " + "; ".join(
                    f"{candidate['part_name']} (ID {candidate['product_id']})" for candidate in suggestions
                ) + ". Please confirm which one you mean."
                response["summary"] = response["assistant_response"]
                if state.get("history"):
                    state["history"][-1]["content"] = response["assistant_response"]
                    save_conversation(conversation_id, state)
        except Exception:
            logger.exception("catalog.suggestion_lookup.failed")
    return response


def _invalid_catalog_data_response(conversation_id: str, state: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    message = (
        f"Catalog product '{row.get('part_name', 'Unknown')}' has invalid dimensions or weight. "
        "Please correct its catalog record before optimizing it."
    )
    response = _reply(conversation_id, state, message, status="catalog_data_invalid")
    response.update({"hitl_required": True, "hitl_reason": message, "product_not_found": False})
    return response


def _ask_add_more(conversation_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    message = generate_conversation_prompt("ask_add_more", state.get("manifest"), state.get("history"))
    state["phase"] = "awaiting_more_items"
    return _reply(conversation_id, state, message, status="awaiting_more_items")


def _start_optimization(
    conversation_id: str,
    state: Dict[str, Any],
    allow_rotation: bool,
    keep_upright: bool,
    max_candidate_packages: int,
    on_stage=None,
) -> Dict[str, Any]:
    if not state.get("manifest"):
        state["phase"] = "gathering"
        return _reply(
            conversation_id,
            state,
            "There are no confirmed items in this task yet. Tell me about the product or part you want to pack.",
        )

    # The conversation manifest is a trust boundary: only confirmed, current
    # catalog rows are allowed to reach the optimizer.
    if on_stage:
        on_stage("Catalog lookup: revalidating every confirmed product")
    catalog_started = time.perf_counter()
    logger.info("workflow.stage.started stage=confirmed_product_catalog_revalidation")
    catalog_manifest: List[Dict[str, Any]] = []
    for item in state["manifest"]:
        product_id = item.get("product_id")
        try:
            row = get_product_by_id(int(product_id)) if product_id is not None else None
        except (TypeError, ValueError):
            row = None
        if not row:
            state["manifest"] = catalog_manifest
            state["phase"] = "gathering"
            return _unknown_catalog_response(conversation_id, state, item)
        try:
            catalog_manifest.append(_catalog_item(row, item.get("quantity")))
        except ValueError:
            return _invalid_catalog_data_response(conversation_id, state, row)
    state["manifest"] = catalog_manifest
    logger.info("workflow.stage.completed stage=confirmed_product_catalog_revalidation products=%d duration_ms=%.2f", len(catalog_manifest), (time.perf_counter() - catalog_started) * 1000)

    from app.agents.workflow import run_unified_workflow

    started = time.perf_counter()
    logger.info("chat.optimization.started conversation_id=%s confirmed_products=%d", conversation_id, len(state["manifest"]))
    result = run_unified_workflow(
        {"items": state["manifest"]},
        allow_rotation=allow_rotation,
        keep_upright=keep_upright,
        max_candidate_packages=max_candidate_packages,
        on_stage=on_stage,
    )
    logger.info("chat.optimization.completed conversation_id=%s duration_ms=%.2f", conversation_id, (time.perf_counter() - started) * 1000)
    state["phase"] = "completed"
    message = result.get("summary", "The packing optimization is complete.")
    state["history"].append({"role": "assistant", "content": message})
    state["history"] = state["history"][-50:]
    save_conversation(conversation_id, state)
    result.update({
        "action": "optimized",
        "conversation_id": conversation_id,
        "task_manifest": state["manifest"],
    })
    return result


def process_chat_turn(
    conversation_id: str,
    user_input: Any,
    *,
    owner_id: str = "local",
    allow_rotation: bool = True,
    keep_upright: bool = False,
    max_candidate_packages: int = 5,
    on_stage=None,
) -> Dict[str, Any]:
    """Process one chat turn against its backend-persisted packaging task."""
    state = load_conversation(conversation_id) or _new_state()
    saved_owner = state.get("owner_id", "local")
    if saved_owner != owner_id:
        raise PermissionError("Conversation not found")
    state["owner_id"] = owner_id
    message = str(user_input if isinstance(user_input, str) else (
        user_input.get("text") or user_input.get("user_input") or user_input.get("part_name") or ""
    )).strip()
    state["history"].append({"role": "user", "content": message})
    state["history"] = state["history"][-50:]

    if state.get("phase") == "completed":
        state.update({"phase": "gathering", "manifest": [], "draft_items": [], "pending_products": []})

    phase = state.get("phase", "gathering")
    confirmed_payload = isinstance(user_input, dict) and bool(user_input.get("confirmed") or user_input.get("is_confirmed"))
    optimize_action = isinstance(user_input, dict) and user_input.get("action") == "optimize"

    if optimize_action:
        if phase == "awaiting_catalog_confirmation":
            return _reply(
                conversation_id,
                state,
                "Please confirm or reject the pending catalog products before optimizing the confirmed task.",
                status="awaiting_confirmation",
            )
        if not state.get("manifest"):
            return _reply(
                conversation_id,
                state,
                "There are no confirmed products in the optimization cart yet. Add and confirm a catalog product first.",
            )
        return _start_optimization(
            conversation_id, state, allow_rotation, keep_upright, max_candidate_packages, on_stage
        )

    if phase == "awaiting_catalog_confirmation":
        if confirmed_payload or _is_yes(message):
            state["manifest"].extend(state.get("pending_products", []))
            state["pending_products"] = []
            return _ask_add_more(conversation_id, state)
        if _is_no(message):
            state["pending_products"] = []
            state["phase"] = "gathering"
            return _reply(conversation_id, state, "Okay, I won't add that catalog match. Tell me the name or ID of a product in the catalog.")
        state["phase"] = "gathering"
        state["pending_products"] = []

    phase = state.get("phase", "gathering")
    if phase == "awaiting_more_items":
        if _is_yes(message):
            state["phase"] = "gathering"
            prompt = generate_conversation_prompt("ask_next_item", state.get("manifest"), state.get("history"))
            return _reply(conversation_id, state, prompt, status="conversation_gathering")
        if _is_no(message):
            return _start_optimization(
                conversation_id, state, allow_rotation, keep_upright, max_candidate_packages, on_stage
            )
        state["phase"] = "gathering"

    prior_history = state["history"][:-1]
    if on_stage:
        on_stage("Requirement agent: interpreting the message and extracting product references")
    extraction = gather_requirements_turn(
        message,
        conversation_history=prior_history,
        accumulated_manifest=state.get("manifest", []),
        draft_items=state.get("draft_items", []),
    )

    candidates = extraction.get("items", [])
    if not candidates:
        return _reply(
            conversation_id,
            state,
            extraction.get("assistant_message") or "What product or part would you like to pack?",
            extraction_method=extraction.get("method"),
        )

    pending_products: List[Dict[str, Any]] = list(state.get("pending_products", []))
    unknown_reference: Optional[Dict[str, Any]] = None

    if on_stage and candidates:
        on_stage("Catalog lookup: checking product IDs and names")
    saw_non_catalog_item = False
    for extracted_item in candidates:
        item = dict(extracted_item)
        item_name = str(item.get("name") or "").strip()
        product_id = item.get("product_id")
        product_row = None
        if product_id is not None:
            try:
                product_row = get_product_by_id(int(product_id))
            except (TypeError, ValueError):
                product_row = None
        elif item.get("catalog_reference") and item_name:
            product_row = get_product_by_name(item_name)

        if product_id is not None and not product_row:
            unknown_reference = item
            continue
        if product_row:
            try:
                catalog_item = _catalog_item(product_row, item.get("quantity"))
            except ValueError:
                return _invalid_catalog_data_response(conversation_id, state, product_row)
            existing = next((p for p in pending_products if p.get("product_id") == catalog_item["product_id"]), None)
            if existing:
                existing["quantity"] += catalog_item["quantity"]
            else:
                pending_products.append(catalog_item)
            continue

        if item.get("catalog_reference"):
            unknown_reference = item
            continue

        # A generic/custom item is still conversational context, not an
        # optimization requirement. Never collect dimensions for it here.
        saw_non_catalog_item = True

    if unknown_reference:
        state["pending_products"] = pending_products
        return _unknown_catalog_response(conversation_id, state, unknown_reference)

    state["draft_items"] = []
    state["pending_products"] = pending_products

    if pending_products:
        return _manifest_confirmation_response(conversation_id, state, extraction.get("method"))

    if saw_non_catalog_item:
        return _reply(
            conversation_id,
            state,
            "I can optimize products that are in the catalog. Which catalog product name or product ID should I look up?",
            extraction_method=extraction.get("method"),
        )

    state["phase"] = "gathering"
    return _reply(
        conversation_id,
        state,
        extraction.get("assistant_message") or "Which product from the catalog would you like to pack? I can only optimize catalog products.",
        extraction_method=extraction.get("method"),
    )
