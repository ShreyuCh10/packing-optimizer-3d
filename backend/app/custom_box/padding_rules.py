
import json
from pathlib import Path

_RULES_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "padding_rules.json"
)


def load_rules() -> dict:
    with open(_RULES_FILE, encoding="utf-8") as file:
        return json.load(file)


def get_rule(item_type: str) -> dict:
    """Find the most suitable padding and stacking rule."""

    rules = load_rules()
    normalized_type = item_type.strip().lower()

    # Exact match first.
    if normalized_type in rules:
        return rules[normalized_type]

    # Match product categories using keywords.
    keyword_mapping = {
        "door": ["door", "wood"],
        "tile": ["tile", "glass", "acrylic", "ceramic"],
        "bottle": ["bottle", "rubber", "plastic", "polymer"],
        "bolt": [
            "bolt",
            "pin",
            "fastener",
            "steel",
            "iron",
            "metal",
            "aluminum",
            "aluminium",
            "brass",
            "bronze",
            "copper",
            "stainless",
            "alloy",
        ],
    }

    for rule_name, keywords in keyword_mapping.items():
        if rule_name in rules and any(
            keyword in normalized_type for keyword in keywords
        ):
            return rules[rule_name]

    return rules["default"]


def get_padding(item_type: str) -> float:
    """Return padding in mm per side."""

    return get_rule(item_type)["padding_mm"]


def get_max_stack(item_type: str) -> int:
    """Return maximum permitted stacking layers."""

    return get_rule(item_type)["max_stack"]


def list_item_types() -> list[str]:
    """Return configured rule names."""

    return [name for name in load_rules() if name != "default"]
