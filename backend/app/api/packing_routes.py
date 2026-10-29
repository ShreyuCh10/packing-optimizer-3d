from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.packing.grid_packer import pack_items_into_container
from app.services.packing.optimizer import optimize_packing, STANDARD_CARTON_SIZES
from app.services.render.viewer import generate_scene_data

router = APIRouter(prefix="/packing", tags=["3D Packing Optimizer"])


class ItemInput(BaseModel):
    id: Optional[str] = Field(default=None, description="Unique item identifier")
    length: float = Field(..., gt=0, description="Item length in mm")
    width: float = Field(..., gt=0, description="Item width in mm")
    height: float = Field(..., gt=0, description="Item height in mm")
    weight: float = Field(default=0.0, ge=0, description="Item weight in kg")
    allow_rotation: bool = Field(default=True, description="Whether 3D rotation is allowed")
    keep_upright: bool = Field(default=False, description="Restrict rotation to yaw only (keep height vertical)")


class ContainerInput(BaseModel):
    name: Optional[str] = Field(default="Container", description="Container name or reference")
    length: float = Field(..., gt=0, description="Container internal length in mm")
    width: float = Field(..., gt=0, description="Container internal width in mm")
    height: float = Field(..., gt=0, description="Container internal height in mm")
    max_weight_kg: Optional[float] = Field(default=1000.0, description="Max container payload in kg")


class PackRequest(BaseModel):
    container: ContainerInput
    items: List[ItemInput]
    allow_rotation: bool = Field(default=True, description="Global allow rotation flag")
    keep_upright: bool = Field(default=False, description="Global keep upright flag")


class OptimizeRequest(BaseModel):
    items: List[ItemInput]
    custom_containers: Optional[List[ContainerInput]] = Field(default=None, description="Optional custom candidate boxes")
    allow_rotation: bool = Field(default=True, description="Global allow rotation flag")
    keep_upright: bool = Field(default=False, description="Global keep upright flag")


@router.get("/cartons", summary="List standard shipping carton dimensions")
def get_standard_cartons():
    """Retrieve predefined standard shipping carton dimensions."""
    return {"cartons": STANDARD_CARTON_SIZES, "total": len(STANDARD_CARTON_SIZES)}


@router.post("/pack", summary="Pack items into a specific container")
def pack_items(req: PackRequest):
    """Pack a list of 3D items into a container, returning coordinates and 3D scene data."""
    if not req.items:
        raise HTTPException(status_code=400, detail="Items list cannot be empty")

    items_dicts = [
        {
            "id": it.id or f"item_{i + 1}",
            "length": it.length,
            "width": it.width,
            "height": it.height,
            "weight": it.weight,
            "allow_rotation": it.allow_rotation,
            "keep_upright": it.keep_upright,
        }
        for i, it in enumerate(req.items)
    ]

    packing_result = pack_items_into_container(
        container_length=req.container.length,
        container_width=req.container.width,
        container_height=req.container.height,
        items=items_dicts,
        allow_rotation=req.allow_rotation,
        keep_upright=req.keep_upright,
    )

    # Attach 3D scene rendering data for frontend visualization
    scene_data = generate_scene_data(packing_result)

    return {
        "packing_result": packing_result,
        "scene_3d": scene_data,
    }


@router.post("/optimize", summary="Find optimal container for item collection")
def optimize_packing_containers(req: OptimizeRequest):
    """Evaluate multiple carton options and return the best fit with highest volume utilization."""
    if not req.items:
        raise HTTPException(status_code=400, detail="Items list cannot be empty")

    items_dicts = [
        {
            "id": it.id or f"item_{i + 1}",
            "length": it.length,
            "width": it.width,
            "height": it.height,
            "weight": it.weight,
            "allow_rotation": it.allow_rotation,
            "keep_upright": it.keep_upright,
        }
        for i, it in enumerate(req.items)
    ]

    candidate_containers = None
    if req.custom_containers:
        candidate_containers = [
            {
                "name": c.name or f"{c.length}x{c.width}x{c.height}",
                "length": c.length,
                "width": c.width,
                "height": c.height,
                "max_weight_kg": c.max_weight_kg or 1000.0,
            }
            for c in req.custom_containers
        ]

    opt_result = optimize_packing(
        items=items_dicts,
        container_sizes=candidate_containers,
        allow_rotation=req.allow_rotation,
        keep_upright=req.keep_upright,
    )

    # Attach 3D scene data for the best option
    if opt_result.get("best_option") and opt_result["best_option"].get("packing_result"):
        opt_result["best_option"]["scene_3d"] = generate_scene_data(opt_result["best_option"]["packing_result"])

    return opt_result
