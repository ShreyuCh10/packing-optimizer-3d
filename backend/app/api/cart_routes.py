"""Cart API Routes.

Provides RESTful endpoints to manage the active packing cart:
- GET /api/cart: Retrieve all items with aggregated volume and weight metrics.
- POST /api/cart: Add a product to cart (auto-populating specs from products table if ID or name provided).
- PUT /api/cart/{item_id}: Update number of parts for a specific cart item.
- DELETE /api/cart/{item_id}: Remove a specific item from the cart.
- DELETE /api/cart: Clear all items from the cart.
- POST /api/cart/optimize: Run the 3D Extreme Point packing solver on all items currently in the cart.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import (
    get_cart_items,
    get_cart_item_by_id,
    add_or_update_cart_item,
    update_cart_item_quantity,
    delete_cart_item,
    clear_cart,
)

router = APIRouter(prefix="/cart", tags=["Packing Cart"])


# ==========================================
# Pydantic Schemas
# ==========================================

class AddToCartInput(BaseModel):
    product_id: Optional[int] = Field(default=None, description="Optional SQLite Product ID to auto-load attributes")
    part_name: Optional[str] = Field(default=None, description="Part name")
    number_of_parts: int = Field(default=1, ge=1, description="Quantity / Number of parts to pack")
    part_type: Optional[str] = Field(default=None, description="Part material type")
    part_length: Optional[float] = Field(default=None, gt=0, description="Part length in mm")
    part_breadth: Optional[float] = Field(default=None, gt=0, description="Part breadth/width in mm")
    part_height: Optional[float] = Field(default=None, gt=0, description="Part height in mm")
    part_weight: Optional[float] = Field(default=None, ge=0, description="Part weight in kg")
    mode: Optional[str] = Field(default="increment", description="'increment' to add to existing, 'set' to overwrite quantity")


class UpdateCartItemInput(BaseModel):
    number_of_parts: int = Field(..., ge=0, description="New number of parts. If 0, item is removed from cart.")


class CartSummary(BaseModel):
    items: List[Dict[str, Any]]
    total_items: int
    total_parts: int
    total_weight_kg: float
    total_volume_liters: float


def compute_cart_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate aggregate metrics for items currently in cart."""
    total_parts = sum(int(it.get("number_of_parts") or 0) for it in items)
    total_weight = sum(float(it.get("line_weight_kg") or 0.0) for it in items)
    total_volume = sum(float(it.get("total_volume_liters") or 0.0) for it in items)

    return {
        "items": items,
        "total_items": len(items),
        "total_parts": total_parts,
        "total_weight_kg": round(total_weight, 3),
        "total_volume_liters": round(total_volume, 3),
    }


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=CartSummary, summary="Fetch all cart items and metrics")
def get_cart():
    """Retrieve all products in the cart with calculated weights, volumes, and summary totals."""
    try:
        items = get_cart_items()
        return compute_cart_summary(items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cart: {str(e)}")


@router.post("", summary="Add a product or custom part to the cart")
def add_to_cart(input_data: AddToCartInput):
    """Add a product to the cart.
    
    If product_id or part_name is found in the products catalog, missing dimensions
    and weights are automatically retrieved from the SQLite database.
    If the product already exists in the cart, the quantity is incremented (or set if mode='set').
    """
    try:
        payload = input_data.model_dump(exclude_none=True)
        saved_item = add_or_update_cart_item(payload)
        items = get_cart_items()
        summary = compute_cart_summary(items)
        return {
            "status": "success",
            "message": f"Added '{saved_item.get('part_name')}' ({saved_item.get('number_of_parts')} units) to cart.",
            "item": saved_item,
            "cart": summary,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to cart: {str(e)}")


@router.put("/{item_id}", summary="Update the number of parts for a cart item")
@router.patch("/{item_id}", summary="Update the number of parts for a cart item")
def update_cart_item(item_id: int, input_data: UpdateCartItemInput):
    """Update number_of_parts for an existing item in the cart.
    
    Setting number_of_parts to 0 removes the item from the cart.
    """
    try:
        updated = update_cart_item_quantity(item_id, input_data.number_of_parts)
        items = get_cart_items()
        summary = compute_cart_summary(items)
        if updated is None:
            return {
                "status": "success",
                "message": f"Cart item #{item_id} removed.",
                "item": None,
                "cart": summary,
            }
        return {
            "status": "success",
            "message": f"Updated '{updated.get('part_name')}' to {updated.get('number_of_parts')} units.",
            "item": updated,
            "cart": summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cart item: {str(e)}")


@router.delete("/{item_id}", summary="Delete an item from the cart")
def delete_cart_item_endpoint(item_id: int):
    """Remove a single product line from the cart by its ID."""
    try:
        success = delete_cart_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Cart item #{item_id} not found.")
        items = get_cart_items()
        summary = compute_cart_summary(items)
        return {
            "status": "success",
            "message": f"Cart item #{item_id} successfully deleted.",
            "cart": summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete cart item: {str(e)}")


@router.delete("", summary="Clear the entire cart")
def clear_cart_endpoint():
    """Empty all products from the cart."""
    try:
        rows_cleared = clear_cart()
        return {
            "status": "success",
            "message": f"Cart cleared ({rows_cleared} items removed).",
            "cart": {
                "items": [],
                "total_items": 0,
                "total_parts": 0,
                "total_weight_kg": 0.0,
                "total_volume_liters": 0.0,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cart: {str(e)}")


@router.post("/optimize", summary="Pack all cart items in 3D using Extreme Point analysis")
def optimize_cart_packing(
    allow_rotation: bool = Query(default=True, description="Allow 3D orthogonal rotations"),
    keep_upright: bool = Query(default=False, description="Restrict rotation to yaw only"),
):
    """Run the cart through the catalog validation and workflow used by chatbot optimization."""
    items = get_cart_items()
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty. Add products to the cart before optimizing.")

    manifest_items = []
    for it in items:
        manifest_items.append({
            "id": f"cart_{it['id']}_{it['part_name'].replace(' ', '_').lower()}",
            "product_id": it.get("product_id"),
            "name": it["part_name"],
            "length": float(it["part_length"]),
            "width": float(it["part_breadth"]),
            "height": float(it["part_height"]),
            "weight": float(it.get("part_weight") or 0.0),
            "quantity": int(it["number_of_parts"]),
            "allow_rotation": allow_rotation,
            "keep_upright": keep_upright,
        })

    try:
        from app.agents.workflow import run_unified_workflow
        return run_unified_workflow({
            "items": manifest_items,
            "allow_rotation": allow_rotation,
            "keep_upright": keep_upright,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cart packing optimization failed: {str(e)}")

