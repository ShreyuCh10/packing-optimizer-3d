import json
from pathlib import Path

_RULES_FILE = Path(__file__).resolve().parents[2]/"data"/"padding_rules.json"

def load_rules() -> dict:
    with open(_RULES_FILE, encoding="utf-8") as f:
        return json.load(f)

def get_rule(item_type: str) -> float:
    """Rule for an item type. Unknown types use 'default'."""
    rules = load_rules()
    return rules.get(item_type.lower(), rules["default"])

def get_padding(item_type: str) -> float:
    """Padding in mm per side"""
    return get_rule(item_type)["padding_mm"]

def get_max_stack(item_type: str) -> int:
    """Maximum number of layers that can be stacked"""
    return get_rule(item_type)["max_stack"]

def list_item_types() -> list[str]:
    """All known item types"""
    return [name for name in load_rules() if name != "default"]