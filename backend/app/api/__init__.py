from app.api.requirement_routes import router as requirement_router
from app.api.custom_box_routes import router as custom_box_router
from app.api.packing_routes import router as packing_router

__all__ = [
    "requirement_router",
    "custom_box_router",
    "packing_router",
]

