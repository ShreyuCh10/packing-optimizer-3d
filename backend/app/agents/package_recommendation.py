import json
import logging
import os
import time
from typing import Any, Dict, List, Literal

from dotenv import find_dotenv, load_dotenv
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for env_file in [
    os.path.join(BACKEND_DIR, ".env"),
    os.path.join(os.path.dirname(BACKEND_DIR), ".env"),
    find_dotenv(),
]:
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file, override=False)

SelectionFactor = Literal[
    "highest_item_volume_utilization",
    "lowest_unoccupied_volume",
    "largest_verified_weight_margin",
]


class PackageRecommendation(BaseModel):
    candidate_id: str = Field(description="Identifier of one provided feasible package candidate")
    selection_factors: List[SelectionFactor] = Field(
        description="Only supported factors from the provided candidate list"
    )


class PackageRecommendationError(RuntimeError):
    pass


def _candidate_id(candidate: Dict[str, Any]) -> str:
    return str(
        candidate.get("package_code")
        or candidate.get("package_id")
        or candidate.get("name")
    )


def _grounded_explanation(
    selected: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    status: str,
) -> Dict[str, Any]:
    name = selected.get("name", "this package")
    quantity = selected.get("quantity", "all")
    utilization = float(selected.get("volume_utilization_pct", 0.0))
    remaining_volume = float(selected.get("wasted_volume_liters", 0.0))
    explanation = (
        f"I recommend {name}. The 3D packing solver confirmed that it fits all {quantity} items. "
        f"It provides {utilization:.2f}% item-volume utilization and leaves "
        f"{remaining_volume:.3f} L of container volume unoccupied."
    )
    factors = [
        f"The packing solver confirmed placement of all {quantity} items.",
        f"Item-volume utilization: {utilization:.2f}%.",
    ]

    payload = selected.get("total_packed_weight_kg")
    capacity = selected.get("max_weight_capacity_kg")
    margin = selected.get("weight_margin_kg")
    if payload is not None and capacity is not None and margin is not None:
        explanation += (
            f" The dataset's payload rating is {float(capacity):g} kg for a "
            f"{float(payload):g} kg shipment ({float(margin):g} kg margin)."
        )
        factors.append(
            f"Verified payload rating: {float(capacity):g} kg "
            f"({float(margin):g} kg margin for this shipment)."
        )

    if selected.get("material") is None:
        explanation += (
            " The package dataset does not specify its material, wall construction, or protection rating; "
            "verify those details before shipping."
        )

    return {
        "status": status,
        "model": None,
        "selected_candidate_id": _candidate_id(selected),
        "assistant_response": explanation,
        "reasoning": explanation,
        "selection_factors": factors,
    }


def _deterministic_recommendation(
    candidates: List[Dict[str, Any]],
    status: str,
) -> Dict[str, Any]:
    selected = max(
        candidates,
        key=lambda item: (
            float(item.get("volume_utilization_pct", 0.0)),
            int(item["inventory"]) if item.get("inventory") is not None else -1,
            -float(item.get("wasted_volume_liters", 0.0)),
        ),
    )
    recommendation = _grounded_explanation(selected, candidates, status)
    if status == "model_not_configured":
        recommendation["assistant_response"] += " The model is not configured."
        recommendation["reasoning"] = recommendation["assistant_response"]
    return recommendation


def recommend_package(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Choose one package from candidates already proven feasible by the packing solver."""
    if not candidates:
        raise ValueError("At least one feasible package candidate is required.")

    candidate_ids = [_candidate_id(candidate) for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("Feasible package candidates must have unique identifiers.")

    foundry_endpoint = os.getenv("AZURE_FOUNDRY_OPENAI_BASE_URL")
    foundry_key = os.getenv("AZURE_FOUNDRY_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")

    if foundry_endpoint and foundry_key:
        model_name = os.getenv("AZURE_FOUNDRY_OPENAI_MODEL", "gpt-5.1")
        model = ChatOpenAI(
            model=model_name,
            base_url=foundry_endpoint,
            api_key=foundry_key,
        ).with_structured_output(PackageRecommendation)
    elif azure_endpoint and azure_key:
        deployment = (
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            or "gpt-5.1"
        ).strip('"\'')
        model_name = os.getenv("AZURE_OPENAI_MODEL_NAME") or deployment
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        model = AzureChatOpenAI(
            azure_deployment=deployment,
            model_name=model_name,
            azure_endpoint=azure_endpoint,
            api_key=azure_key,
            api_version=api_version,
            temperature=float(os.getenv("AZURE_OPENAI_TEMPERATURE", 0.0)),
        ).with_structured_output(PackageRecommendation)
    else:
        status = "single_feasible_candidate" if len(candidates) == 1 else "model_not_configured"
        return _deterministic_recommendation(candidates, status)

    candidate_data = [
        {
            "candidate_id": _candidate_id(candidate),
            "name": candidate.get("name"),
            "category": candidate.get("category"),
            "material": candidate.get("material"),
            "inner_dimensions_mm": candidate.get("inner_dimensions_mm"),
            "max_weight_capacity_kg": candidate.get("max_weight_capacity_kg"),
            "inventory": candidate.get("inventory"),
            "volume_utilization_pct": candidate.get("volume_utilization_pct"),
            "padded_bbox_utilization_pct": candidate.get("padded_bbox_utilization_pct"),
            "wasted_volume_liters": candidate.get("wasted_volume_liters"),
            "packed_weight_kg": candidate.get("total_packed_weight_kg"),
            "weight_margin_kg": candidate.get("weight_margin_kg"),
        }
        for candidate in candidates
    ]
    prompt = [
        (
            "system",
            "You are a packaging recommendation analyst. Choose exactly one package only from the "
            "provided candidates. Every candidate passed deterministic 3D fit and weight checks. "
            "Use only candidate data; null or missing properties are unknown. Do not infer material, "
            "wall construction, protection, inventory, handling performance, product movement, or "
            "fragility suitability. volume_utilization_pct is solid product volume divided by internal "
            "container volume; padded_bbox_utilization_pct is a separate estimate. Return the exact "
            "candidate_id and only applicable selection_factors from the allowed enum. Do not produce "
            "free-form explanation text.",
        ),
        (
            "human",
            "Select one package for this product and quantity. Product requirements: "
            f"{json.dumps({'name': candidates[0].get('product_name'), 'quantity': candidates[0].get('quantity')})}. "
            f"Feasible candidates: {json.dumps(candidate_data)}",
        ),
    ]

    started = time.perf_counter()
    logger.info("llm.call.started operation=package_recommendation model=%s", model_name)
    try:
        response: PackageRecommendation = model.invoke(prompt)
        logger.info("llm.call.completed operation=package_recommendation duration_ms=%.2f", (time.perf_counter() - started) * 1000)
    except Exception as exc:
        logger.exception("llm.call.failed operation=package_recommendation duration_ms=%.2f", (time.perf_counter() - started) * 1000)
        fallback = _deterministic_recommendation(candidates, "model_call_failed")
        fallback["reasoning"] += " A deterministic fallback was used because the recommendation model call failed."
        fallback["error"] = "model_call_failed"
        return fallback

    selected_id = str(response.candidate_id)
    if selected_id not in candidate_ids:
        raise PackageRecommendationError(
            "Azure AI Foundry selected a package that was not in the feasible candidate list."
        )

    selected = next(candidate for candidate in candidates if _candidate_id(candidate) == selected_id)
    recommendation = _grounded_explanation(selected, candidates, "model_recommended")
    recommendation["model"] = model_name
    return recommendation
