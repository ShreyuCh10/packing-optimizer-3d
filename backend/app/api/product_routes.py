from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.db import get_all_products, get_product_by_name, get_product_by_id

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", summary="List all products from SQLite database")
def list_products(
    search: Optional[str] = Query(default=None, description="Filter products by part name or material type"),
    part_type: Optional[str] = Query(default=None, description="Filter by exact part type"),
    limit: Optional[int] = Query(default=None, ge=1, description="Limit results"),
    offset: int = Query(default=0, ge=0, description="Offset results"),
):
    """Retrieve products directly from SQLite database."""
    items = get_all_products()

    # Normalize defaults if called directly outside FastAPI
    search_val = search if isinstance(search, str) else None
    type_val = part_type if isinstance(part_type, str) else None
    offset_val = offset if isinstance(offset, int) else 0
    limit_val = limit if isinstance(limit, int) else None

    if search_val:
        s = search_val.strip().lower()
        items = [
            p for p in items
            if s in p.get("part_name", "").lower() or s in p.get("part_type", "").lower()
        ]

    if type_val:
        t = type_val.strip().lower()
        items = [p for p in items if p.get("part_type", "").lower() == t]

    total = len(items)

    if limit_val is not None:
        items = items[offset_val : offset_val + limit_val]
    elif offset_val > 0:
        items = items[offset_val:]

    return {
        "products": items,
        "total": total,
        "source": "sqlite",
    }


@router.get("/{part_identifier}", summary="Get a product by ID or part name")
def get_product(part_identifier: str):
    """Retrieve a single product by numeric ID or exact part name."""
    product = None

    if part_identifier.isdigit():
        product = get_product_by_id(int(part_identifier))

    if not product:
        product = get_product_by_name(part_identifier)

    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{part_identifier}' not found in database.")

    return product
