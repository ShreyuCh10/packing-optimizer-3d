import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from app.db import get_all_products, get_product_by_name, get_product_by_id
from app.services.mesh_service import get_product_mesh_glb

router = APIRouter(prefix="/products", tags=["Products"])

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


@router.get("/{part_identifier}/mesh", summary="Get 3D mesh GLB for frontend rendering")
def get_product_mesh(part_identifier: str):
    """Serve a GLB 3D mesh generated or converted by Python's trimesh for WebGL/Three.js rendering."""
    product = None

    if part_identifier.isdigit():
        product = get_product_by_id(int(part_identifier))

    if not product:
        product = get_product_by_name(part_identifier)

    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{part_identifier}' not found in database.")

    try:
        glb_bytes, is_cad, filename = get_product_mesh_glb(product)
        headers = {
            "Content-Disposition": f'inline; filename="{os.path.splitext(filename)[0]}.glb"',
            "X-Is-Cad-Model": "true" if is_cad else "false",
            "X-Mesh-Source": "step-cad" if is_cad else "trimesh-procedural",
            "Access-Control-Expose-Headers": "X-Is-Cad-Model, X-Mesh-Source",
        }
        return Response(content=glb_bytes, media_type="model/gltf-binary", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate 3D mesh with trimesh: {e}")


@router.get("/{part_identifier}/model", summary="Download/serve 3D CAD model file")
def get_product_model(part_identifier: str):
    """Retrieve and serve the raw 3D model file (e.g. .STEP) for a product if available."""
    product = None

    if part_identifier.isdigit():
        product = get_product_by_id(int(part_identifier))

    if not product:
        product = get_product_by_name(part_identifier)

    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{part_identifier}' not found in database.")

    model_file = product.get("model_file")
    if not model_file:
        raise HTTPException(status_code=404, detail=f"No 3D CAD model associated with '{product.get('part_name')}'.")

    # Resolve file path
    file_path = os.path.join(BACKEND_DIR, "data", model_file)
    if not os.path.exists(file_path):
        file_path = os.path.join(BACKEND_DIR, "data", "models", os.path.basename(model_file))

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"3D Model file '{model_file}' not found on server disk.")

    filename = os.path.basename(file_path)
    return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")
