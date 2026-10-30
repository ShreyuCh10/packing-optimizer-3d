from fastapi import APIRouter, HTTPException, Response

from app.custom_box.constraints import (
    MAX_MECHANICAL_KG,
    ConstraintError,
    check_constraints,
)
from app.custom_box.multi_unit import find_max_units, size_box_for_units
from app.custom_box.padding_rules import get_max_stack, get_padding, list_item_types
from app.models import CustomBoxRequest, CustomBoxResult
from app.render.viewer import render_custom_box

router = APIRouter()


def _design(request: CustomBoxRequest) -> CustomBoxResult:
    """Shared by both routes, so the box and the 3D model never disagree."""
    item = request.item
    padding = get_padding(item.item_type)
    max_stack = get_max_stack(item.item_type)

    # Until the frontend sends a handling mode, assume forklift / trolley.
    max_weight = MAX_MECHANICAL_KG

    try:
        if item.quantity is None:
            # No quantity given: estimate how many units fit
            return find_max_units(item, padding, max_stack, max_weight)

        # Quantity given: size a box for exactly that many
        result = size_box_for_units(item, padding, max_stack)
        check_constraints(item, result, max_weight)
        return result
    except ConstraintError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/custom-box", response_model=CustomBoxResult)
def create_custom_box(request: CustomBoxRequest):
    return _design(request)


@router.post("/custom-box/model")
def create_custom_box_model(request: CustomBoxRequest):
    result = _design(request)
    glb = render_custom_box(result)
    return Response(content=glb, media_type="model/gltf-binary")


@router.get("/item-types")
def get_item_types():
    return {"item_types": list_item_types()}