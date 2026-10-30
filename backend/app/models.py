from pydantic import BaseModel, Field

class Dimensions(BaseModel):
    """Item or box dimensions. All values are in millimetres."""
    length: float = Field(gt=0) #rejects 0 and negatives gt = greater than
    width: float = Field(gt=0)
    height: float = Field(gt=0)

class Item(BaseModel):
    """A product to be packed. Dimensions in mm, weight in kg."""
    item_type: str = "default"
    dimensions: Dimensions
    weight: float | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=1)

class Placement(BaseModel):
    """One item inside the box. position=its minimum corner, in mm"""
    position: tuple[float, float, float]
    size: Dimensions

class CustomBoxRequest(BaseModel):
    item: Item

class CustomBoxResult(BaseModel):
    """Dimensions in mm, volume in mm³, utilization as a fraction 0 to 1."""
    box_dimensions: Dimensions
    volume: float = Field(gt=0)
    utilization: float = Field(ge=0, le=1)
    padding_used: float = Field(ge=0)
    units_packed: int = Field(ge=1)
    placements: list[Placement]



