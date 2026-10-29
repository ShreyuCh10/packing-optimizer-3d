import json
import os
from typing import Dict, Any, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "padding_rules.json")


def load_padding_rules() -> Dict[str, Any]:
    """Load padding rules configuration."""
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "rules": [],
        "default_rule": {
            "recommended_padding": "epe_foam",
            "thickness_mm": 15.0,
            "min_clearance_mm": 5.0,
            "fragility": "medium"
        }
    }


def get_padding_for_part(part_type: str) -> Dict[str, Any]:
    """Retrieve the recommended padding rule for a given part type/material."""
    data = load_padding_rules()
    target = (part_type or "").strip().lower()

    for rule in data.get("rules", []):
        if rule.get("part_type", "").lower() == target:
            return rule

    # Fuzzy match keywords
    for rule in data.get("rules", []):
        rule_type = rule.get("part_type", "").lower()
        if rule_type in target or target in rule_type:
            return rule

    return data.get("default_rule", {
        "recommended_padding": "epe_foam",
        "thickness_mm": 15.0,
        "min_clearance_mm": 5.0,
        "fragility": "medium"
    })

