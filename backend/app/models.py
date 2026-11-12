
from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class Item(BaseModel):
    item_type: str = "default"
    dimensions: Dimensions
    weight: float = Field(gt=0)
    quantity: int | None = Field(default=None, ge=1)
    model_file: str | None = None


class CustomBoxConstraints(BaseModel):
    max_box_dimensions: Dimensions
    max_human_lifting_weight_kg: float = Field(gt=0)
    padding_per_side_mm: float = Field(ge=0)
    wall_thickness_mm: float = Field(gt=0)
    material_id: str = Field(min_length=1)


class Placement(BaseModel):
    position: tuple[float, float, float]
    size: Dimensions


class CustomBoxRequest(BaseModel):
    item: Item
    constraints: CustomBoxConstraints


class CustomBoxResult(BaseModel):
    box_dimensions: Dimensions
    volume: float = Field(gt=0)
    utilization: float = Field(ge=0, le=1)
    padding_used: float = Field(ge=0)
    units_packed: int = Field(ge=1)
    placements: list[Placement]

    # Weight calculations (kg)
    product_unit_weight_kg: float = Field(default=0, ge=0)
    total_product_weight_kg: float = Field(default=0, ge=0)
    packaging_weight_kg: float = Field(default=0, ge=0)
    total_weight_kg: float = Field(default=0, ge=0)

    # Packaging material details
    material_id: str = ""
    material_name: str = ""
    wall_thickness_mm: float = Field(default=0, ge=0)


class BoxModelPreviewRequest(BaseModel):
    result: CustomBoxResult
    model_file: str | None = None
    include_measurements: bool = False


class AutomaticCustomBoxRequest(BaseModel):
    item: Item
    total_quantity: int = Field(ge=1)
    constraints: CustomBoxConstraints


class AutomaticCustomBoxResult(BaseModel):
    total_quantity: int
    boxes_required: int
    material_id: str
    material_name: str
    boxes: list[CustomBoxResult]

    total_product_weight_kg: float
    total_packaging_weight_kg: float
    total_weight_kg: float
    estimated_packaging_cost: float
