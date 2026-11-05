import csv
import io
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.db import (
    get_all_products,
    get_product_by_name,
    get_product_by_id,
    insert_product,
    insert_products_batch,
)
from app.services.mesh_service import get_product_mesh_glb

router = APIRouter(prefix="/products", tags=["Products"])

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class CreateProductInput(BaseModel):
    part_name: str = Field(..., min_length=1, description="Part name (unique)")
    part_length: float = Field(..., gt=0, description="Part length in mm")
    part_breadth: float = Field(..., gt=0, description="Part breadth/width in mm")
    part_height: float = Field(..., gt=0, description="Part height in mm")
    part_weight: float = Field(..., ge=0, description="Part weight in kg")
    part_type: str = Field(default="Standard", description="Part type or material classification")
    standard_no_of_parts: int = Field(default=1, ge=1, description="Standard Pack Quantity (SNP)")
    domestic_or_international: str = Field(default="Domestic", description="Domestic or International")
    per_day_requirement: int = Field(default=100, ge=0, description="Per day requirement")
    minimum_order_quantity: int = Field(default=1, ge=1, description="Minimum order quantity (MOQ)")
    line_feeding_method: str = Field(default="Two-Bin System", description="Line feeding method")
    model_file: Optional[str] = Field(default=None, description="CAD model file path (optional)")


def parse_csv_products(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse CSV bytes into normalized product dictionaries."""
    text = file_content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    products = []
    for row in reader:
        clean_row = {
            str(k).strip().lower(): str(v).strip()
            for k, v in row.items()
            if k is not None
        }

        name = (
            clean_row.get("part_name")
            or clean_row.get("name")
            or clean_row.get("part name")
            or clean_row.get("product_name")
            or clean_row.get("product name")
        )
        if not name:
            continue

        length = (
            clean_row.get("part_length")
            or clean_row.get("length")
            or clean_row.get("part length")
            or clean_row.get("length (mm)")
            or clean_row.get("length_mm")
        )
        breadth = (
            clean_row.get("part_breadth")
            or clean_row.get("part_width")
            or clean_row.get("width")
            or clean_row.get("breadth")
            or clean_row.get("part width")
            or clean_row.get("width (mm)")
            or clean_row.get("width_mm")
        )
        height = (
            clean_row.get("part_height")
            or clean_row.get("height")
            or clean_row.get("part height")
            or clean_row.get("height (mm)")
            or clean_row.get("height_mm")
        )
        weight = (
            clean_row.get("part_weight")
            or clean_row.get("weight")
            or clean_row.get("part weight")
            or clean_row.get("weight (kg)")
            or clean_row.get("weight_kg")
        )
        part_type = (
            clean_row.get("part_type")
            or clean_row.get("material")
            or clean_row.get("part type")
            or clean_row.get("type")
        )
        snp = (
            clean_row.get("standard_no_of_parts")
            or clean_row.get("snp")
            or clean_row.get("standard no of parts")
            or clean_row.get("pack_quantity")
            or clean_row.get("quantity")
        )
        market = (
            clean_row.get("domestic_or_international")
            or clean_row.get("market")
            or clean_row.get("domestic/international")
            or clean_row.get("origin")
        )
        per_day = (
            clean_row.get("per_day_requirement")
            or clean_row.get("daily_requirement")
            or clean_row.get("per day requirement")
            or clean_row.get("daily requirement")
        )
        moq = (
            clean_row.get("minimum_order_quantity")
            or clean_row.get("moq")
            or clean_row.get("minimum order quantity")
        )
        feeding = (
            clean_row.get("line_feeding_method")
            or clean_row.get("line feeding method")
            or clean_row.get("feeding_method")
            or clean_row.get("line feeding")
        )
        model_file = (
            clean_row.get("model_file")
            or clean_row.get("model")
            or clean_row.get("model file")
            or clean_row.get("cad_model")
        )

        try:
            l_val = float(length) if length else 100.0
        except ValueError:
            l_val = 100.0
        try:
            b_val = float(breadth) if breadth else 50.0
        except ValueError:
            b_val = 50.0
        try:
            h_val = float(height) if height else 30.0
        except ValueError:
            h_val = 30.0
        try:
            w_val = float(weight) if weight else 0.5
        except ValueError:
            w_val = 0.5
        try:
            snp_val = int(float(snp)) if snp else 1
        except ValueError:
            snp_val = 1
        try:
            day_val = int(float(per_day)) if per_day else 100
        except ValueError:
            day_val = 100
        try:
            moq_val = int(float(moq)) if moq else 1
        except ValueError:
            moq_val = 1

        products.append({
            "part_name": name,
            "part_length": max(0.1, l_val),
            "part_breadth": max(0.1, b_val),
            "part_height": max(0.1, h_val),
            "part_weight": max(0.001, w_val),
            "part_type": part_type or "Standard",
            "standard_no_of_parts": max(1, snp_val),
            "domestic_or_international": "International" if (market and "int" in market.lower()) else "Domestic",
            "per_day_requirement": max(0, day_val),
            "minimum_order_quantity": max(1, moq_val),
            "line_feeding_method": feeding or "Two-Bin System",
            "model_file": model_file or None,
        })
    return products


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



@router.post("", summary="Create a new product in SQLite database")
def create_product(product_in: CreateProductInput):
    """Add a new product to the catalog."""
    try:
        data = product_in.model_dump()
        result = insert_product(data)
        return {
            "success": True,
            "message": f"Product '{product_in.part_name}' added successfully.",
            "product": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add product: {str(e)}")


@router.post("/upload-csv", summary="Upload CSV file to import products")
async def upload_csv_products(file: UploadFile = File(...)):
    """Upload a CSV file containing multiple products or a single product."""
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .csv file")
    try:
        content_bytes = await file.read()
        parsed_products = parse_csv_products(content_bytes)
        if not parsed_products:
            raise HTTPException(status_code=400, detail="No valid product rows found in the CSV file.")

        batch_result = insert_products_batch(parsed_products)
        return {
            "success": True,
            "message": f"Successfully imported {batch_result['added_count']} product(s) from '{file.filename}'.",
            "added_count": batch_result["added_count"],
            "total_processed": batch_result["total_processed"],
            "errors": batch_result["errors"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV file: {str(e)}")


@router.post("/batch", summary="Batch add multiple products via JSON")
def batch_add_products(products_in: List[CreateProductInput]):
    """Batch add multiple products via JSON array."""
    try:
        products_list = [p.model_dump() for p in products_in]
        batch_result = insert_products_batch(products_list)
        return {
            "success": True,
            "message": f"Processed {batch_result['total_processed']} products ({batch_result['added_count']} added/updated).",
            **batch_result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Batch insert failed: {str(e)}")


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
