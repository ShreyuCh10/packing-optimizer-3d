
import csv
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from app.custom_box.constraints import (
    ConstraintError,
    check_constraints,
)
from app.custom_box.multi_unit import (
    calculate_packaging_weight,
    find_max_units,
    size_box_for_units,
)
from app.custom_box.padding_rules import (
    get_max_stack,
    get_padding,
    list_item_types,
)
from app.models import (
    AutomaticCustomBoxRequest,
    AutomaticCustomBoxResult,
    BoxModelPreviewRequest,
    CustomBoxRequest,
    CustomBoxResult,
)
from app.render.viewer import (
    render_empty_box,
    render_packed_box,
)

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Preferred structural box material based on product material.
PRODUCT_BOX_MATERIAL_RULES = {
    "glass": ["corrugated-triple-wall", "wooden-crate"],
    "electronics": ["corrugated-double-wall", "corrugated-triple-wall"],
    "steel": ["corrugated-double-wall", "corrugated-triple-wall", "wooden-crate"],
    "iron": ["corrugated-double-wall", "corrugated-triple-wall", "wooden-crate"],
    "brass": ["corrugated-double-wall", "corrugated-triple-wall"],
    "bronze": ["corrugated-double-wall", "corrugated-triple-wall"],
    "copper": ["corrugated-double-wall", "corrugated-triple-wall"],
    "stainless": ["corrugated-double-wall", "corrugated-triple-wall"],
    "aluminum": ["corrugated-double-wall", "corrugated-triple-wall"],
    "aluminium": ["corrugated-double-wall", "corrugated-triple-wall"],
    "plastic": ["corrugated-single-wall", "polypropylene-corrugated", "corrugated-double-wall"],
    "nylon": ["corrugated-single-wall", "polypropylene-corrugated"],
    "pom": ["corrugated-single-wall", "polypropylene-corrugated"],
    "rubber": ["corrugated-single-wall", "polypropylene-corrugated"],
    "wood": ["corrugated-triple-wall", "wooden-crate"],
}

DEFAULT_BOX_MATERIALS = [
    "corrugated-double-wall",
    "corrugated-triple-wall",
    "wooden-crate",
]


def _get_suitable_box_material_ids(item_type: str) -> list[str]:
    """Return preferred box materials based on the product material."""

    normalized_type = (item_type or "").strip().lower()

    for product_material, box_materials in PRODUCT_BOX_MATERIAL_RULES.items():
        if product_material in normalized_type:
            return box_materials

    return DEFAULT_BOX_MATERIALS


def _load_materials():
    materials_path = DATA_DIR / "materials.json"

    if not materials_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Packaging materials configuration is unavailable.",
        )

    try:
        with materials_path.open("r", encoding="utf-8-sig") as file:
            materials = json.load(file)

        if not isinstance(materials, list):
            raise ValueError("Materials configuration must be a list.")

        return materials

    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load packaging materials: {exc}",
        )


def _get_selected_material(material_id: str):
    materials = _load_materials()

    material = next(
        (m for m in materials if m.get("id") == material_id),
        None,
    )

    if material is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown packaging material: {material_id}",
        )

    try:
        density = float(material["density_kg_m3"])
        max_weight = float(material["max_weight_kg"])
        wall_thickness = float(material["wall_thickness_mm"])

        if min(density, max_weight, wall_thickness) <= 0:
            raise ValueError(
                "Material density, capacity and wall thickness must be positive."
            )

        return material, density, max_weight, wall_thickness

    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid material configuration: {exc}",
        )


def _design(request: CustomBoxRequest) -> CustomBoxResult:
    """Calculate box dimensions, packaging weight and total packed weight."""

    item = request.item
    constraints = request.constraints

    material, density, material_max_weight, wall_thickness = (
        _get_selected_material(constraints.material_id)
    )

    # Padding and stacking limits come from product-type rules.
    padding = get_padding(item.item_type)
    max_stack = get_max_stack(item.item_type)

    # Respect both material capacity and human lifting limit.
    effective_weight_limit = min(
        constraints.max_human_lifting_weight_kg,
        material_max_weight,
    )

    try:
        if item.quantity is None:
            # Manual capacity calculation: maximum units in one box.
            result = find_max_units(
                item=item,
                padding=padding,
                max_stack=max_stack,
                max_weight_kg=effective_weight_limit,
                max_box_dimensions=constraints.max_box_dimensions,
                wall_thickness_mm=wall_thickness,
                density_kg_m3=density,
            )

        else:
            # Fixed quantity calculation: size one box for this quantity.
            result = size_box_for_units(
                item=item,
                padding=padding,
                max_stack=max_stack,
                wall_thickness_mm=wall_thickness,
                max_box_dimensions=constraints.max_box_dimensions,
            )

        # Estimate the six-wall packaging weight.
        packaging_weight = calculate_packaging_weight(
            box_dimensions=result.box_dimensions,
            wall_thickness_mm=wall_thickness,
            density_kg_m3=density,
        )

        # Calculate product and total weights.
        unit_weight = item.weight
        total_product_weight = unit_weight * result.units_packed
        total_weight = total_product_weight + packaging_weight

        # Validate dimensions and combined weight.
        check_constraints(
            item=item.model_copy(
                update={"quantity": result.units_packed}
            ),
            result=result,
            max_weight_kg=effective_weight_limit,
            max_box_dimensions=constraints.max_box_dimensions,
            packaging_weight_kg=packaging_weight,
        )

        # Return the original result with additional calculated details.
        return result.model_copy(
            update={
                "padding_used": padding,
                "product_unit_weight_kg": unit_weight,
                "total_product_weight_kg": total_product_weight,
                "packaging_weight_kg": packaging_weight,
                "total_weight_kg": total_weight,
                "material_id": material["id"],
                "material_name": material["name"],
                "wall_thickness_mm": wall_thickness,
            }
        )

    except ConstraintError as exc:
        raise HTTPException(status_code=422, detail=str(exc))



def _box_surface_area_sqm(result: CustomBoxResult) -> float:
    """Calculate the outer surface area of a six-sided box in m²."""

    length = result.box_dimensions.length
    width = result.box_dimensions.width
    height = result.box_dimensions.height

    area_mm2 = 2 * (
        length * width
        + length * height
        + width * height
    )

    return area_mm2 / 1_000_000



@router.post(
    "/custom-box/automatic",
    response_model=AutomaticCustomBoxResult,
)
def create_automatic_custom_boxes(
    request: AutomaticCustomBoxRequest,
):
    """Automatically select a suitable box material and distribute quantity."""

    item = request.item
    total_quantity = request.total_quantity
    materials = _load_materials()

    candidates = []
    suitable_material_ids = _get_suitable_box_material_ids(item.item_type)

    for material_id in suitable_material_ids:
        material = next(
            (m for m in materials if m.get("id") == material_id),
            None,
        )

        if material is None:
            continue

        try:
            material_cost = float(material["cost_per_sqm"])

            if material_cost <= 0:
                continue

            _, density, material_max_weight, wall_thickness = (
                _get_selected_material(material_id)
            )

            padding = get_padding(item.item_type)
            max_stack = get_max_stack(item.item_type)

            effective_weight_limit = min(
                request.constraints.max_human_lifting_weight_kg,
                material_max_weight,
            )

            capacity_result = find_max_units(
                item=item.model_copy(update={"quantity": None}),
                padding=padding,
                max_stack=max_stack,
                max_weight_kg=effective_weight_limit,
                max_box_dimensions=request.constraints.max_box_dimensions,
                wall_thickness_mm=wall_thickness,
                density_kg_m3=density,
            )

            capacity = capacity_result.units_packed

            if capacity < 1:
                continue

            remaining = total_quantity
            box_results = []

            while remaining > 0:
                quantity_for_box = min(remaining, capacity)

                box_request = CustomBoxRequest(
                    item=item.model_copy(
                        update={"quantity": quantity_for_box}
                    ),
                    constraints=request.constraints.model_copy(
                        update={"material_id": material_id}
                    ),
                )

                box_result = _design(box_request)
                box_results.append(box_result)
                remaining -= quantity_for_box

            total_cost = sum(
                _box_surface_area_sqm(box) * material_cost
                for box in box_results
            )

            total_product_weight = sum(
                box.total_product_weight_kg
                for box in box_results
            )

            total_packaging_weight = sum(
                box.packaging_weight_kg
                for box in box_results
            )

            candidates.append({
                "material_id": material_id,
                "material_name": material["name"],
                "boxes": box_results,
                "total_product_weight": total_product_weight,
                "total_packaging_weight": total_packaging_weight,
                "total_weight": (
                    total_product_weight + total_packaging_weight
                ),
                "total_cost": total_cost,
            })

        except (ConstraintError, KeyError, TypeError, ValueError):
            continue

    if not candidates:
        raise HTTPException(
            status_code=422,
            detail=(
                "No suitable packaging material can safely pack "
                "the requested quantity within the specified constraints."
            ),
        )

    # First feasible material in product-specific priority order.
    best = candidates[0]

    return AutomaticCustomBoxResult(
        total_quantity=total_quantity,
        boxes_required=len(best["boxes"]),
        material_id=best["material_id"],
        material_name=best["material_name"],
        boxes=best["boxes"],
        total_product_weight_kg=best["total_product_weight"],
        total_packaging_weight_kg=best["total_packaging_weight"],
        total_weight_kg=best["total_weight"],
        estimated_packaging_cost=best["total_cost"],
    )


@router.post("/custom-box", response_model=CustomBoxResult)
def create_custom_box(request: CustomBoxRequest):
    return _design(request)


@router.post("/custom-box/empty-model")
def create_empty_box_model(request: CustomBoxRequest):
    result = _design(request)
    glb = render_empty_box(result)

    return Response(
        content=glb,
        media_type="model/gltf-binary",
    )


@router.post("/custom-box/packed-model")
def create_packed_box_model(request: CustomBoxRequest):
    result = _design(request)

    model_file = request.item.model_file

    if not model_file:
        raise HTTPException(
            status_code=422,
            detail="A 3D model is not available for this product.",
        )

    model_name = Path(model_file).name

    if not model_name.lower().endswith(".glb"):
        model_name = Path(model_name).with_suffix(".glb").name

    model_path = DATA_DIR / "models" / model_name

    try:
        glb = render_packed_box(result, model_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return Response(
        content=glb,
        media_type="model/gltf-binary",
    )



@router.post("/custom-box/empty-model/result")
def create_empty_box_model_from_result(
    request: BoxModelPreviewRequest,
):
    glb = render_empty_box(
        request.result,
        show_measurements=request.include_measurements,
    )

    return Response(
        content=glb,
        media_type="model/gltf-binary",
    )

@router.post("/custom-box/packed-model/result")
def create_packed_box_model_from_result(
    request: BoxModelPreviewRequest,
):
    if not request.model_file:
        raise HTTPException(
            status_code=422,
            detail="A 3D model is not available for this product.",
        )

    model_name = Path(request.model_file).name

    if not model_name.lower().endswith(".glb"):
        model_name = Path(model_name).with_suffix(".glb").name

    model_path = DATA_DIR / "models" / model_name

    try:
        glb = render_packed_box(request.result, model_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return Response(
        content=glb,
        media_type="model/gltf-binary",
    )



@router.get("/item-types")
def get_item_types():
    return {"item_types": list_item_types()}


@router.get("/products")
def get_products():
    dataset_path = DATA_DIR / "products_dataset.csv"

    if not dataset_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Product dataset is unavailable.",
        )

    numeric_fields = {
        "part_length",
        "part_breadth",
        "part_height",
        "part_weight",
        "standard_no_of_parts",
        "per_day_requirement",
        "minimum_order_quantity",
    }

    try:
        with dataset_path.open(
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            products = []

            for row in csv.DictReader(file):
                for field in numeric_fields:
                    value = row.get(field)

                    if value not in (None, ""):
                        row[field] = float(value)

                products.append(row)

            return products

    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read product dataset: {exc}",
        )


@router.get("/materials")
def get_materials():
    return {"materials": _load_materials()}
