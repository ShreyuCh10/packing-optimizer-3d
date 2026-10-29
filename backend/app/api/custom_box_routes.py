import json
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.custom_box.padding_rules import get_padding_for_part, load_padding_rules
from app.custom_box.sizing import calculate_box_dimensions
from app.custom_box.constraints import validate_box_constraints
from app.custom_box.multi_unit import calculate_multi_unit_layout

router = APIRouter(prefix="/custom-box", tags=["Custom Box Sizing"])

MATERIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "materials.json")


def _load_materials() -> List[Dict[str, Any]]:
    if os.path.exists(MATERIALS_PATH):
        try:
            with open(MATERIALS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


class CustomBoxCalculationRequest(BaseModel):
    part_length: float = Field(..., gt=0, description="Part length in mm")
    part_width: float = Field(..., gt=0, description="Part width in mm")
    part_height: float = Field(..., gt=0, description="Part height in mm")
    part_weight: float = Field(..., ge=0, description="Part weight in kg")
    part_type: str = Field(default="standard", description="Material type (e.g. steel, aluminum, glass, plastic)")
    quantity: int = Field(default=1, ge=1, description="Quantity / SNP (Standard Number of Packs)")
    material_id: Optional[str] = Field(default="corrugated-double-wall", description="Packaging material ID")
    custom_padding_thickness_mm: Optional[float] = Field(default=None, description="Override padding thickness in mm")


@router.get("/materials", summary="List available packaging box materials")
def get_materials():
    """Retrieve the list of supported box packaging materials."""
    materials = _load_materials()
    return {"materials": materials, "total": len(materials)}


@router.get("/padding-rules", summary="List padding rules by part material")
def get_padding_rules():
    """Retrieve standard padding recommendations based on part fragility and material."""
    rules_data = load_padding_rules()
    return rules_data


@router.post("/calculate", summary="Calculate custom box dimensions, padding, and constraints")
def calculate_custom_box(req: CustomBoxCalculationRequest):
    """Calculate the custom box dimensions, multi-unit layout, padding, and structural constraints."""
    materials = _load_materials()
    chosen_material = next((m for m in materials if m.get("id") == req.material_id), None)
    if not chosen_material:
        chosen_material = materials[1] if len(materials) > 1 else {
            "id": "default",
            "name": "Standard Corrugated",
            "wall_thickness_mm": 6.0,
            "max_weight_kg": 35.0,
            "density_kg_m3": 160.0,
            "cost_per_sqm": 2.00,
        }

    # 1. Multi-unit arrangement if quantity > 1
    multi_unit_info = calculate_multi_unit_layout(
        part_length=req.part_length,
        part_width=req.part_width,
        part_height=req.part_height,
        part_weight=req.part_weight,
        quantity=req.quantity,
    )
    content_dims = multi_unit_info["content_dimensions_mm"]
    total_part_weight = multi_unit_info["total_part_weight_kg"]

    # 2. Padding determination
    padding_rule = get_padding_for_part(req.part_type)
    padding_thickness = (
        req.custom_padding_thickness_mm
        if req.custom_padding_thickness_mm is not None
        else padding_rule.get("thickness_mm", 15.0)
    )

    # 3. Box sizing
    wall_thickness = float(chosen_material.get("wall_thickness_mm", 6.0))
    density = float(chosen_material.get("density_kg_m3", 160.0))
    cost_per_sqm = float(chosen_material.get("cost_per_sqm", 2.0))

    sizing = calculate_box_dimensions(
        content_length=content_dims["length"],
        content_width=content_dims["width"],
        content_height=content_dims["height"],
        padding_thickness=padding_thickness,
        wall_thickness=wall_thickness,
        content_weight=total_part_weight,
        material_density_kg_m3=density,
        cost_per_sqm=cost_per_sqm,
    )

    # 4. Constraints validation
    external_dims = sizing["external_dimensions_mm"]
    gross_weight = sizing["weights_kg"]["gross"]
    max_weight = float(chosen_material.get("max_weight_kg", 35.0))

    constraints_check = validate_box_constraints(
        external_length_mm=external_dims["length"],
        external_width_mm=external_dims["width"],
        external_height_mm=external_dims["height"],
        gross_weight_kg=gross_weight,
        material_max_weight_kg=max_weight,
    )

    return {
        "part_specification": {
            "dimensions_mm": {"length": req.part_length, "width": req.part_width, "height": req.part_height},
            "weight_kg": req.part_weight,
            "type": req.part_type,
            "quantity": req.quantity,
        },
        "multi_unit_arrangement": multi_unit_info,
        "padding": {
            "applied_thickness_mm": padding_thickness,
            "recommended_material": padding_rule.get("recommended_padding"),
            "fragility": padding_rule.get("fragility"),
        },
        "material": chosen_material,
        "box_sizing": sizing,
        "constraints_validation": constraints_check,
    }
