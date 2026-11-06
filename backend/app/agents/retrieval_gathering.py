"""Retrieval and Gathering Agent

A fully deterministic system that takes part/packaging requirements
(from the Requirement Gathering Agent, database product lookup, or raw specifications) and:
1. Resolves specifications (auto-populating from SQLite `products` table if product_id or part_name is provided).
2. Calculates deterministic physical metrics:
   - max_rating (total payload rating = part_weight * snp)
   - single_product_volume (cm³ and liters)
   - total_product_volume (liters)
   - total_product_weight (kg)
   - fragility & padding rules based on material definition
   - multi-unit bounding box for SNP > 1
   - total volume and bounding box required including protective padding
3. Queries actual SQLite database tables:
   - 'packages' (41 standard cartons with interior dimensions, max part payload, and pallet stacking)
   - 'metal_stillages' (5 heavy-duty transport stillages for larger/heavier payloads)
   - 'metal_pallets' (5 heavy-duty metal pallets)
   - 'base_pallets' (3 standard base pallets)
   - Filters by 3D orthogonal spatial fit, weight capacity, and inventory > 0.
4. Narrows down to the most useful packages:
   - Eliminates excessively oversized containers that waste volume.
   - Ranks options by item-volume utilization and reports padded-bounds utilization separately.
   - Categorizes them into fit tiers:
     * 🥇 Best Fit (Optimal Volume Utilization)
     * 🥈 Comfort Fit (Buffered Clearance for handling & extra dunnage)
     * 🥉 Balanced Alternative
     * 🏗️ Heavy-Duty / Bulk Option (when payload exceeds carton limits or heavy industrial)
"""

import csv
import os
import re
import sqlite3
from typing import TypedDict, List, Dict, Any, Optional, Union, Tuple

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# Try importing domain helpers from services.custom_box, with resilient fallbacks
try:
    from app.services.custom_box.padding_rules import get_padding_for_part
except ImportError:
    def get_padding_for_part(part_type: str) -> Dict[str, Any]:
        target = (part_type or "").strip().lower()
        if any(k in target for k in ["glass", "ceramic", "fragile"]):
            return {"part_type": part_type, "recommended_padding": "epe_foam", "thickness_mm": 30.0, "fragility": "high"}
        if any(k in target for k in ["electronics", "pcb", "chip", "sensor"]):
            return {"part_type": part_type, "recommended_padding": "esd_anti_static_foam", "thickness_mm": 25.0, "fragility": "high"}
        if any(k in target for k in ["steel", "iron", "cast", "hardened"]):
            return {"part_type": part_type, "recommended_padding": "dense_eva_foam", "thickness_mm": 20.0, "fragility": "medium"}
        if any(k in target for k in ["plastic", "poly", "nylon", "pom"]):
            return {"part_type": part_type, "recommended_padding": "bubble_wrap", "thickness_mm": 10.0, "fragility": "low"}
        if any(k in target for k in ["wood", "timber"]):
            return {"part_type": part_type, "recommended_padding": "polyethylene_foam", "thickness_mm": 12.0, "fragility": "medium"}
        return {"part_type": part_type, "recommended_padding": "polyethylene_foam", "thickness_mm": 15.0, "fragility": "medium"}

try:
    from app.services.custom_box.multi_unit import calculate_multi_unit_layout
except ImportError:
    def calculate_multi_unit_layout(part_length: float, part_width: float, part_height: float, part_weight: float, quantity: int = 1) -> Dict[str, Any]:
        return {
            "quantity": quantity,
            "grid": {"nx": 1, "ny": quantity, "nz": 1},
            "content_dimensions_mm": {"length": part_length, "width": round(part_width * quantity, 2), "height": part_height},
            "total_part_weight_kg": round(part_weight * quantity, 3),
            "divider_thickness_mm": 3.0,
            "alternative_layouts_count": 1,
        }

# Database path resolution
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "data", "products.db")
DB_PATH = os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a SQLite database connection with Row factory."""
    path = db_path or DB_PATH
    if not os.path.isabs(path) and not os.path.exists(path):
        candidate = os.path.join(BACKEND_DIR, path)
        if os.path.exists(candidate):
            path = candidate
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# Schema Definitions
# ==========================================

class PartRequirements(BaseModel):
    product_id: Optional[int] = Field(default=None, description="Optional SQLite Product ID to auto-load attributes")
    name: Optional[str] = Field(default="Part", description="Name of the part")
    description: Optional[str] = Field(default="", description="Detailed description")
    snp: Optional[Union[int, str]] = Field(default=None, description="Standard Number of Packs (SNP)")
    part_length: Optional[float] = Field(default=None, gt=0, description="Length in mm")
    part_width: Optional[float] = Field(default=None, gt=0, description="Width in mm")
    part_height: Optional[float] = Field(default=None, gt=0, description="Height in mm")
    part_type: Optional[str] = Field(default=None, description="Material definition (e.g. steel, aluminum, glass, plastic)")
    part_weight: Optional[float] = Field(default=None, ge=0, description="Weight of single part in kg")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CalculatedProductMetrics(BaseModel):
    part_name: str
    part_type: str
    snp: int
    max_rating: float
    single_product_dimensions_mm: Dict[str, float]
    single_product_volume_cm3: float
    single_product_volume_liters: float
    total_product_volume_liters: float
    total_product_weight_kg: float
    fragility: str
    recommended_padding_material: str
    recommended_padding_thickness_mm: float
    multi_unit_grid: Dict[str, int]
    content_dimensions_mm: Dict[str, float]
    effective_bounding_box_mm: Dict[str, float]
    total_volume_required_liters: float


class RetrievalGatheringState(TypedDict, total=False):
    requirements: Dict[str, Any]
    metrics: Dict[str, Any]
    matching_packages: List[Dict[str, Any]]
    recommended_package: Optional[Dict[str, Any]]
    all_fitting_candidates: List[Dict[str, Any]]
    total_candidates_found: int
    narrowed_count: int
    narrowing_summary: str
    tables_queried: List[str]
    packages_table_exists: bool
    status: str
    message: Optional[str]


# ==========================================
# Database Auto-Lookup & Metrics Calculation
# ==========================================

def parse_snp(raw_snp: Any) -> int:
    """Safely extract integer SNP (Standard Number of Packs)."""
    if isinstance(raw_snp, (int, float)):
        return max(1, int(raw_snp))
    if isinstance(raw_snp, str):
        match = re.search(r"\d+", raw_snp)
        if match:
            return max(1, int(match.group(0)))
    return 1


def resolve_requirements_from_db(
    data: Dict[str, Any],
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """If product_id or part_name is specified and physical attributes are missing,
    auto-populate dimensions, weight, SNP, and material from the SQLite 'products' table.
    """
    resolved = dict(data)
    if resolved.get("catalog_lookup") is False:
        return resolved
    product_id = resolved.get("product_id")
    part_name = resolved.get("name") or resolved.get("part_name")

    db_row: Optional[Dict[str, Any]] = None

    try:
        conn = get_db_connection(db_path)
        with conn:
            cursor = conn.cursor()
            if product_id is not None and str(product_id).isdigit():
                cursor.execute("SELECT * FROM products WHERE id = ? LIMIT 1", (int(product_id),))
                r = cursor.fetchone()
                if r:
                    db_row = dict(r)

            if not db_row and part_name:
                cursor.execute(
                    "SELECT * FROM products WHERE LOWER(part_name) = LOWER(?) LIMIT 1",
                    (str(part_name).strip(),)
                )
                r = cursor.fetchone()
                if r:
                    db_row = dict(r)
        conn.close()
    except Exception:
        pass

    if db_row:
        # Auto-populate missing values from the database record
        if resolved.get("part_length") is None:
            resolved["part_length"] = float(db_row.get("part_length", 100.0))
        if resolved.get("part_width") is None:
            resolved["part_width"] = float(db_row.get("part_breadth", 80.0))
        if resolved.get("part_height") is None:
            resolved["part_height"] = float(db_row.get("part_height", 50.0))
        if resolved.get("part_weight") is None:
            resolved["part_weight"] = float(db_row.get("part_weight", 1.0))
        if not resolved.get("part_type"):
            resolved["part_type"] = str(db_row.get("part_type", "Standard"))
        if resolved.get("snp") is None:
            resolved["snp"] = int(db_row.get("standard_no_of_parts", 1))
        if not resolved.get("name") or resolved.get("name") == "Part":
            resolved["name"] = str(db_row.get("part_name", "Part"))
        resolved["matched_product_id"] = db_row.get("id")

    return resolved


def calculate_metrics(
    requirements_input: Union[BaseModel, Dict[str, Any]],
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate deterministic physical metrics from input requirements."""
    if hasattr(requirements_input, "model_dump"):
        raw_data = requirements_input.model_dump()
    elif isinstance(requirements_input, dict):
        raw_data = dict(requirements_input)
    else:
        raise ValueError(f"Unsupported requirements type: {type(requirements_input)}")

    # Auto-resolve from database if product_id or part_name is provided
    data = resolve_requirements_from_db(raw_data, db_path=db_path)

    # Check for multi-item cart manifest
    if data.get("items") and isinstance(data["items"], list) and len(data["items"]) > 0:
        total_vol = 0.0
        total_wt = 0.0
        max_l, max_w, max_h = 0.0, 0.0, 0.0
        total_qty = 0
        resolved_items = []
        for it in data["items"]:
            rit = resolve_requirements_from_db(it, db_path=db_path)
            l = float(rit.get("part_length") or rit.get("length") or 100.0)
            w = float(rit.get("part_width") or rit.get("part_breadth") or rit.get("width") or 80.0)
            h = float(rit.get("part_height") or rit.get("height") or 50.0)
            wt = float(rit.get("part_weight") or rit.get("weight") or 1.0)
            qty = max(1, int(rit.get("quantity") or rit.get("number_of_parts") or rit.get("snp") or 1))
            total_vol += (l * w * h / 1000000.0) * qty
            total_wt += wt * qty
            max_l = max(max_l, l)
            max_w = max(max_w, w)
            max_h = max(max_h, h)
            total_qty += qty
            rit["length"] = l
            rit["width"] = w
            rit["height"] = h
            rit["weight"] = wt
            rit["quantity"] = qty
            resolved_items.append(rit)

        padding_thickness = 15.0
        padding_material = "polyethylene_foam"
        fragility = "medium"
        eff_l = round(max_l + (2 * padding_thickness), 2)
        eff_w = round(max_w + (2 * padding_thickness), 2)
        eff_h = round(max_h + (2 * padding_thickness), 2)
        vol_req = round(max(total_vol * 1.25, (eff_l * eff_w * eff_h) / 1000000.0), 4)

        return {
            "part_name": data.get("name") or data.get("part_name") or f"Cart Manifest ({total_qty} units)",
            "matched_product_id": None,
            "part_type": "Mixed Manifest",
            "snp": total_qty,
            "max_rating": round(total_wt, 3),
            "single_product_dimensions_mm": {"length": max_l, "width": max_w, "height": max_h},
            "single_product_volume_cm3": round(max_l * max_w * max_h / 1000.0, 3),
            "single_product_volume_liters": round(max_l * max_w * max_h / 1000000.0, 4),
            "total_product_volume_liters": round(total_vol, 4),
            "total_product_weight_kg": round(total_wt, 3),
            "fragility": fragility,
            "recommended_padding_material": padding_material,
            "recommended_padding_thickness_mm": padding_thickness,
            "padding_volume_liters": round(max(0.0, vol_req - total_vol), 4),
            "multi_unit_layout": {"quantity": total_qty, "items_count": len(resolved_items)},
            "effective_bounding_box_mm": {"length": eff_l, "width": eff_w, "height": eff_h},
            "total_volume_required_liters": vol_req,
            "items": resolved_items,
        }

    # Extract dimensions with fallbacks
    length = float(data.get("part_length") or data.get("length") or 100.0)
    width = float(data.get("part_width") or data.get("part_breadth") or data.get("width") or 80.0)
    height = float(data.get("part_height") or data.get("parth_height") or data.get("height") or 50.0)
    weight = float(data.get("part_weight") or data.get("weight") or 1.0)
    part_type = str(data.get("part_type") or data.get("material") or "standard")
    snp = parse_snp(data.get("snp", 1))

    # 1. Max Rating (total product payload = weight * snp)
    max_rating = round(weight * snp, 3)

    # 2. Volumes
    single_vol_cm3 = round((length * width * height) / 1000.0, 3)
    single_vol_liters = round(single_vol_cm3 / 1000.0, 4)
    total_product_vol_liters = round(single_vol_liters * snp, 4)
    total_product_weight_kg = max_rating

    # 3. Fragility & Padding Determination
    padding_info = get_padding_for_part(part_type)
    fragility = padding_info.get("fragility", "medium")
    padding_thickness = float(padding_info.get("thickness_mm", 15.0))
    padding_material = padding_info.get("recommended_padding", "polyethylene_foam")

    # 4. Multi-Unit 3D Layout (for SNP >= 1)
    multi_unit = calculate_multi_unit_layout(
        part_length=length,
        part_width=width,
        part_height=height,
        part_weight=weight,
        quantity=snp,
    )
    content_dims = multi_unit.get(
        "content_dimensions_mm",
        {"length": length, "width": round(width * snp, 2), "height": height}
    )
    grid = multi_unit.get("grid", {"nx": 1, "ny": snp, "nz": 1})

    # 5. Total Effective Dimensions (content + 2*padding on all 3 axes)
    eff_length = round(content_dims["length"] + (2 * padding_thickness), 2)
    eff_width = round(content_dims["width"] + (2 * padding_thickness), 2)
    eff_height = round(content_dims["height"] + (2 * padding_thickness), 2)

    total_volume_required_liters = round((eff_length * eff_width * eff_height) / 1000000.0, 4)

    return {
        "part_name": data.get("name") or data.get("part_name") or "Part",
        "matched_product_id": data.get("matched_product_id"),
        "part_type": part_type,
        "snp": snp,
        "max_rating": max_rating,
        "single_product_dimensions_mm": {"length": length, "width": width, "height": height},
        "single_product_volume_cm3": single_vol_cm3,
        "single_product_volume_liters": single_vol_liters,
        "total_product_volume_liters": total_product_vol_liters,
        "total_product_weight_kg": total_product_weight_kg,
        "fragility": fragility,
        "recommended_padding_material": padding_material,
        "recommended_padding_thickness_mm": padding_thickness,
        "multi_unit_grid": grid,
        "content_dimensions_mm": content_dims,
        "effective_bounding_box_mm": {"length": eff_length, "width": eff_width, "height": eff_height},
        "total_volume_required_liters": total_volume_required_liters,
    }


# ==========================================
# 3D Orthogonal Fit Validation
# ==========================================

def check_3d_fits(content_dims: List[float], box_dims: List[float]) -> bool:
    """Check if content fits inside box under any of the 6 orthogonal rotations.

    A 3D box A can fit inside box B (under some orthogonal rotation)
    if and only if sorted(A) <= sorted(B) element-wise.
    """
    sorted_content = sorted(content_dims)
    sorted_box = sorted(box_dims)
    return (
        sorted_content[0] <= sorted_box[0] and
        sorted_content[1] <= sorted_box[1] and
        sorted_content[2] <= sorted_box[2]
    )


# ==========================================
# Database Packaging Query & Narrowing Engine
# ==========================================

def fetch_all_candidates_from_db(
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Fetch packaging candidates directly from actual SQLite tables:
    - 'packages' (Carton boxes)
    - 'metal_stillages' (Heavy transport stillages)
    - 'metal_pallets' (Heavy metal pallets)
    - 'base_pallets' (Base wooden pallets)

    Returns:
        (candidates_list, tables_queried)
    """
    candidates: List[Dict[str, Any]] = []
    tables_queried: List[str] = []

    try:
        conn = get_db_connection(db_path)
        with conn:
            cursor = conn.cursor()

            # 1. Standard Cartons (table: packages)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type IN ('table', 'view') AND LOWER(name) = 'packages'
            """)
            if cursor.fetchone():
                tables_queried.append("packages")
                cursor.execute("SELECT * FROM packages ORDER BY id ASC")
                for r in cursor.fetchall():
                    row = dict(r)
                    candidates.append({
                        "package_id": row.get("id"),
                        "package_code": str(row.get("package", f"PKG-{row.get('id')}")),
                        "name": str(row.get("package")),
                        "category": "carton",
                        "category_label": "Carton Box",
                        "inner_length_mm": float(row.get("inner_length_mm") or row.get("outer_length_mm") or 300.0),
                        "inner_width_mm": float(row.get("inner_width_mm") or row.get("outer_width_mm") or 200.0),
                        "inner_height_mm": float(row.get("inner_height_mm") or row.get("outer_height_mm") or 100.0),
                        "outer_length_mm": float(row.get("outer_length_mm") or 300.0),
                        "outer_width_mm": float(row.get("outer_width_mm") or 200.0),
                        "outer_height_mm": float(row.get("outer_height_mm") or 100.0),
                        "max_weight_capacity_kg": float(row.get("part_weight_kg") or row.get("total_weight_kg") or 9.0),
                        "empty_weight_kg": float(row.get("empty_weight_kg") or 1.0),
                        "inventory": int(row["inventory"]) if row.get("inventory") is not None else None,
                        "pallet_info": {
                            "pallet_length_mm": row.get("pallet_length_mm"),
                            "pallet_width_mm": row.get("pallet_width_mm"),
                            "pallet_height_mm": row.get("pallet_height_mm"),
                            "bins_per_row": row.get("bins_per_row"),
                            "bins_per_column": row.get("bins_per_column"),
                            "layers_per_pallet": row.get("layers_per_pallet"),
                            "bins_per_pallet": row.get("bins_per_pallet"),
                            "stack_height_mm": row.get("stack_height_mm"),
                            "pallet_load_weight_kg": row.get("pallet_load_weight_kg"),
                        },
                        "material": None,
                    })

            # 2. Metal Stillages (table: metal_stillages)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type IN ('table', 'view') AND LOWER(name) = 'metal_stillages'
            """)
            if cursor.fetchone():
                tables_queried.append("metal_stillages")
                cursor.execute("SELECT * FROM metal_stillages ORDER BY id ASC")
                for r in cursor.fetchall():
                    row = dict(r)
                    candidates.append({
                        "package_id": row.get("id"),
                        "package_code": str(row.get("metal_stillage", f"STILLAGE-{row.get('id')}")),
                        "name": str(row.get("metal_stillage")),
                        "category": "metal_stillage",
                        "category_label": "Metal Stillage",
                        "inner_length_mm": float(row.get("inner_length_mm")),
                        "inner_width_mm": float(row.get("inner_width_mm")),
                        "inner_height_mm": float(row.get("inner_height_mm")),
                        "outer_length_mm": float(row.get("outer_length_mm")),
                        "outer_width_mm": float(row.get("outer_width_mm")),
                        "outer_height_mm": float(row.get("outer_height_mm")),
                        "max_weight_capacity_kg": None,
                        "empty_weight_kg": float(row.get("empty_weight_kg", 65.0)),
                        "inventory": None,
                        "pallet_info": None,
                        "material": None,
                    })

            # 3. Metal Pallets (table: metal_pallets)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type IN ('table', 'view') AND LOWER(name) = 'metal_pallets'
            """)
            if cursor.fetchone():
                tables_queried.append("metal_pallets")
                cursor.execute("SELECT * FROM metal_pallets ORDER BY id ASC")
                for r in cursor.fetchall():
                    row = dict(r)
                    candidates.append({
                        "package_id": row.get("id"),
                        "package_code": str(row.get("metal_pallet", f"MPALLET-{row.get('id')}")),
                        "name": str(row.get("metal_pallet")),
                        "category": "metal_pallet",
                        "category_label": "Metal Pallet",
                        "inner_length_mm": float(row.get("inner_length_mm")),
                        "inner_width_mm": float(row.get("inner_width_mm")),
                        "inner_height_mm": float(row.get("inner_height_mm")),
                        "outer_length_mm": float(row.get("outer_length_mm")),
                        "outer_width_mm": float(row.get("outer_width_mm")),
                        "outer_height_mm": float(row.get("outer_height_mm")),
                        "max_weight_capacity_kg": None,
                        "empty_weight_kg": float(row.get("empty_weight_kg", 28.0)),
                        "inventory": None,
                        "pallet_info": None,
                        "material": None,
                    })

            # 4. Base Pallets (table: base_pallets)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type IN ('table', 'view') AND LOWER(name) = 'base_pallets'
            """)
            if cursor.fetchone():
                tables_queried.append("base_pallets")
                cursor.execute("SELECT * FROM base_pallets ORDER BY id ASC")
                for r in cursor.fetchall():
                    row = dict(r)
                    candidates.append({
                        "package_id": row.get("id"),
                        "package_code": str(row.get("base_pallet", f"BPALLET-{row.get('id')}")),
                        "name": str(row.get("base_pallet")),
                        "category": "base_pallet",
                        "category_label": "Base Pallet",
                        "inner_length_mm": float(row.get("outer_length_mm")),
                        "inner_width_mm": float(row.get("outer_width_mm")),
                        "inner_height_mm": 0.0,
                        "outer_length_mm": float(row.get("outer_length_mm")),
                        "outer_width_mm": float(row.get("outer_width_mm")),
                        "outer_height_mm": float(row.get("outer_height_mm")),
                        "max_weight_capacity_kg": None,
                        "empty_weight_kg": float(row.get("empty_weight_kg", 26.0)),
                        "inventory": None,
                        "pallet_info": None,
                        "material": None,
                    })

        conn.close()
    except sqlite3.Error as exc:
        raise RuntimeError(f"Could not read package data from SQLite: {exc}") from exc

    # Use the authoritative package dataset when the database has not been migrated.
    if not any(candidate["category"] == "carton" for candidate in candidates):
        packages_csv = os.path.join(BACKEND_DIR, "data", "packages.csv")
        try:
            with open(packages_csv, "r", encoding="utf-8", newline="") as source:
                package_rows = csv.DictReader(source)
                for row in package_rows:
                    name = row["package"].strip()
                    candidates.append({
                        "package_id": name,
                        "package_code": name,
                        "name": name,
                        "category": "carton",
                        "category_label": "Carton Box",
                        "inner_length_mm": float(row["inner_length_mm"]),
                        "inner_width_mm": float(row["inner_width_mm"]),
                        "inner_height_mm": float(row["inner_height_mm"]),
                        "outer_length_mm": float(row["outer_length_mm"]),
                        "outer_width_mm": float(row["outer_width_mm"]),
                        "outer_height_mm": float(row["outer_height_mm"]),
                        "max_weight_capacity_kg": float(row["part_weight_kg"]),
                        "empty_weight_kg": float(row["empty_weight_kg"]),
                        "inventory": None,
                        "pallet_info": None,
                        "material": None,
                    })
        except (OSError, KeyError, ValueError) as exc:
            raise RuntimeError(f"Could not load authoritative package dataset {packages_csv}: {exc}") from exc
            candidates.append({
                "package_id": p["package_code"],
                "package_code": p["package_code"],
                "name": p["name"],
                "category": p["category"],
                "category_label": "Carton Box",
                "inner_length_mm": p["inner_length_mm"],
                "inner_width_mm": p["inner_width_mm"],
                "inner_height_mm": p["inner_height_mm"],
                "outer_length_mm": p["outer_length_mm"],
                "outer_width_mm": p["outer_width_mm"],
                "outer_height_mm": p["outer_height_mm"],
                "max_weight_capacity_kg": p["max_weight_capacity"],
                "empty_weight_kg": 1.2,
                "inventory": p["inventory"],
                "pallet_info": None,
                "material": p["material"],
            })

    return candidates, tables_queried


def narrow_down_packages(
    candidates: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    max_results: int = 5,
) -> Dict[str, Any]:
    """Evaluate physical fit and intelligently narrow down the matching packages.

    Narrowing criteria:
    1. Feasibility: not out of stock when stock is known, 3D orthogonal fit, and a verified weight capacity.
    2. Efficiency: calculates item-volume utilization and padded-bounds utilization separately.
    3. Categorization & Prioritization:
       - If payload fits standard cartons (<= 9kg), cartons are prioritized as primary parcel options.
       - If payload exceeds standard carton capacity (> 9kg) or is heavy industrial, stillages/pallets
         are selected as primary heavy-duty transport options.
    4. Curates the top 3-5 narrowed packages with actionable fit tiers:
       - Rank 1: Best Fit (Optimal Volume Utilization)
       - Rank 2: Comfort Fit (Buffered Clearance for handling & extra padding)
       - Rank 3: Balanced Stacking Alternative
       - Plus heavy-duty option if applicable.
    """
    eff_dims = metrics["effective_bounding_box_mm"]
    req_l = eff_dims["length"]
    req_w = eff_dims["width"]
    req_h = eff_dims["height"]
    max_rating = metrics["max_rating"]
    vol_required = metrics["total_volume_required_liters"]

    all_fitting: List[Dict[str, Any]] = []

    for pkg in candidates:
        inventory_value = pkg.get("inventory")
        inventory = int(inventory_value) if inventory_value is not None else None
        if inventory is not None and inventory <= 0:
            continue

        box_l = float(pkg["inner_length_mm"])
        box_w = float(pkg["inner_width_mm"])
        box_h = float(pkg["inner_height_mm"])
        max_weight_value = pkg.get("max_weight_capacity_kg")
        max_wt = float(max_weight_value) if max_weight_value is not None else None

        # Check 3D geometric orthogonal fit
        fits_3d = check_3d_fits([req_l, req_w, req_h], [box_l, box_w, box_h])

        # Check weight capacity
        fits_weight = max_wt is not None and max_wt >= max_rating

        if fits_3d and fits_weight:
            box_volume_liters = round((box_l * box_w * box_h) / 1000000.0, 3)
            item_volume_liters = float(metrics.get("total_product_volume_liters", 0.0))
            utilization_pct = round(
                (item_volume_liters / max(0.001, box_volume_liters)) * 100.0,
                2,
            )
            padded_bbox_utilization_pct = round(
                (vol_required / max(0.001, box_volume_liters)) * 100.0,
                1,
            )
            remaining_volume_liters = round(
                max(0.0, box_volume_liters - item_volume_liters),
                3,
            )
            padded_bbox_clearance_liters = round(
                max(0.0, box_volume_liters - vol_required),
                3,
            )

            # Dimensional slack (sum of clearance mm along best aligned axes)
            s_content = sorted([req_l, req_w, req_h])
            s_box = sorted([box_l, box_w, box_h])
            slack_mm = round((s_box[0] - s_content[0]) + (s_box[1] - s_content[1]) + (s_box[2] - s_content[2]), 1)

            all_fitting.append({
                "package_id": pkg.get("package_id"),
                "package_code": pkg.get("package_code"),
                "name": pkg.get("name"),
                "category": pkg.get("category", "carton"),
                "category_label": pkg.get("category_label", "Packaging"),
                "inner_dimensions_mm": {"length": box_l, "width": box_w, "height": box_h},
                "outer_dimensions_mm": {
                    "length": pkg.get("outer_length_mm", box_l),
                    "width": pkg.get("outer_width_mm", box_w),
                    "height": pkg.get("outer_height_mm", box_h),
                },
                "max_weight_capacity_kg": max_wt,
                "empty_weight_kg": pkg.get("empty_weight_kg", 1.0),
                "inventory": inventory,
                "box_volume_liters": box_volume_liters,
                "volume_utilization_pct": min(100.0, utilization_pct),
                "padded_bbox_utilization_pct": min(100.0, padded_bbox_utilization_pct),
                "wasted_volume_liters": remaining_volume_liters,
                "padded_bbox_clearance_liters": padded_bbox_clearance_liters,
                "slack_clearance_mm": slack_mm,
                "pallet_info": pkg.get("pallet_info"),
                        "material": pkg.get("material"),
            })

    # Sort all fitting packages by volume utilization descending
    all_fitting.sort(key=lambda p: p["volume_utilization_pct"], reverse=True)

    # Separate into cartons vs heavy-duty stillages/pallets
    cartons = [p for p in all_fitting if p["category"] == "carton"]
    heavy_duty = [p for p in all_fitting if p["category"] in ("metal_stillage", "metal_pallet", "base_pallets")]

    narrowed: List[Dict[str, Any]] = []
    summary_text = ""

    if cartons:
        # Curate top cartons based on volume utilization
        top_util = cartons[0]["volume_utilization_pct"]
        cutoff = top_util * 0.3 if top_util >= 5.0 else 0.0
        filtered_cartons = [c for c in cartons if c["volume_utilization_pct"] >= cutoff]
        selected_cartons = (filtered_cartons if filtered_cartons else cartons)[:max_results]

        for idx, c in enumerate(selected_cartons, 1):
            if idx == 1:
                tier = "Best Fit (Optimal Utilization)"
                badge = "Recommended"
            elif idx == 2:
                tier = "Comfort Fit (Buffered Clearance)"
                badge = "Alternative"
            else:
                tier = "Balanced Stacking Option"
                badge = "Alternative"

            c_copy = dict(c)
            c_copy["rank"] = idx
            c_copy["fit_tier"] = tier
            c_copy["badge"] = badge
            narrowed.append(c_copy)

        # If heavy-duty stillages also fit, add the top stillage as a heavy-duty option
        if heavy_duty and len(narrowed) < max_results + 1:
            hd = dict(heavy_duty[0])
            hd["rank"] = len(narrowed) + 1
            hd["fit_tier"] = "Heavy-Duty / Bulk Transport"
            hd["badge"] = "Bulk Option"
            narrowed.append(hd)

        summary_text = (
            f"Narrowed down from {len(all_fitting)} fitting packages in database "
            f"to the {len(narrowed)} most useful packages based on volume utilization and minimum void fill."
        )

    elif heavy_duty:
        # Standard cartons could not fit (likely weight > 9kg or large dimensions)
        selected_hd = heavy_duty[:max_results]
        for idx, hd in enumerate(selected_hd, 1):
            hd_copy = dict(hd)
            hd_copy["rank"] = idx
            hd_copy["fit_tier"] = "Heavy-Duty Transport (Optimal)" if idx == 1 else "Heavy-Duty (Alternative)"
            hd_copy["badge"] = "Heavy-Duty Recommended" if idx == 1 else "Alternative"
            narrowed.append(hd_copy)

        summary_text = (
            f"Payload ({max_rating} kg) exceeds standard carton capacity (max 9.0 kg). "
            f"Successfully narrowed down to {len(narrowed)} heavy-duty metal stillages / pallets."
        )

    else:
        summary_text = (
            f"No package with a verified payload rating can accommodate the required dimensions "
            f"({req_l}x{req_w}x{req_h} mm) and payload ({max_rating} kg). Add rated heavy-duty packaging "
            "data before making a recommendation."
        )

    best_match = narrowed[0] if narrowed else None

    return {
        "matching_packages": narrowed,
        "recommended_package": best_match,
        "all_fitting_candidates": all_fitting,
        "total_fitting_in_db": len(all_fitting),
        "narrowed_count": len(narrowed),
        "narrowing_summary": summary_text,
    }


def query_candidate_packages(
    metrics: Dict[str, Any],
    db_path: Optional[str] = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Query actual SQLite database tables and narrow down to the most useful packages."""
    target_db = db_path or DB_PATH
    candidates, tables_queried = fetch_all_candidates_from_db(target_db)

    narrowed_result = narrow_down_packages(
        candidates=candidates,
        metrics=metrics,
        max_results=max_results,
    )

    return {
        "packages_table_exists": len(tables_queried) > 0,
        "database_path": os.path.abspath(target_db),
        "tables_queried": tables_queried,
        "matching_packages": narrowed_result["matching_packages"],
        "recommended_package": narrowed_result["recommended_package"],
        "all_fitting_candidates": narrowed_result["all_fitting_candidates"],
        "total_fitting_in_db": narrowed_result["total_fitting_in_db"],
        "narrowed_count": narrowed_result["narrowed_count"],
        "narrowing_summary": narrowed_result["narrowing_summary"],
    }


# ==========================================
# LangGraph Workflow Implementation
# ==========================================

def calculate_metrics_node(state: RetrievalGatheringState) -> Dict[str, Any]:
    """Node 1: Deterministically compute physical dimensions, ratings, and padding."""
    requirements = state.get("requirements", {})
    metrics = calculate_metrics(requirements)
    return {"metrics": metrics}


def query_packages_node(state: RetrievalGatheringState) -> Dict[str, Any]:
    """Node 2: Query actual SQLite tables, evaluate physical fit, and narrow down useful packages."""
    metrics = state.get("metrics", {})
    query_result = query_candidate_packages(metrics)

    packages = query_result["matching_packages"]
    table_exists = query_result["packages_table_exists"]

    status = "packages_found" if packages else "no_fitting_package_in_stock"
    message = query_result["narrowing_summary"]

    return {
        "matching_packages": packages,
        "recommended_package": query_result.get("recommended_package"),
        "total_candidates_found": query_result["total_fitting_in_db"],
        "narrowed_count": query_result["narrowed_count"],
        "narrowing_summary": query_result["narrowing_summary"],
        "tables_queried": query_result["tables_queried"],
        "packages_table_exists": table_exists,
        "status": status,
        "message": message,
    }


# Construct StateGraph
retrieval_agent = StateGraph(RetrievalGatheringState)

retrieval_agent.add_node("calculate_metrics", calculate_metrics_node)
retrieval_agent.add_node("query_packages", query_packages_node)

retrieval_agent.add_edge(START, "calculate_metrics")
retrieval_agent.add_edge("calculate_metrics", "query_packages")
retrieval_agent.add_edge("query_packages", END)

# Compiled LangGraph runnable
app = retrieval_agent.compile()


# ==========================================
# Standalone Direct Callable
# ==========================================

def run_retrieval_gathering(
    requirements: Union[BaseModel, Dict[str, Any]],
    db_path: Optional[str] = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Standalone entrypoint to run the Retrieval & Gathering agent directly."""
    req_dict = requirements.model_dump() if hasattr(requirements, "model_dump") else dict(requirements)

    metrics = calculate_metrics(req_dict, db_path=db_path)
    query_result = query_candidate_packages(metrics, db_path=db_path, max_results=max_results)

    packages = query_result["matching_packages"]
    status = "packages_found" if packages else "no_fitting_package_in_stock"

    return {
        "requirements": req_dict,
        "metrics": metrics,
        "recommended_package": query_result.get("recommended_package"),
        "matching_packages": packages,
        "all_fitting_candidates": query_result.get("all_fitting_candidates", []),
        "total_candidates_found": query_result["total_fitting_in_db"],
        "narrowed_count": query_result["narrowed_count"],
        "narrowing_summary": query_result["narrowing_summary"],
        "tables_queried": query_result["tables_queried"],
        "packages_table_exists": query_result["packages_table_exists"],
        "status": status,
    }


# ==========================================
# Standalone CLI Self-Test
# ==========================================

if __name__ == "__main__":
    print("=" * 70)
    print("Retrieval & Gathering Agent: SQLite Database Integration & Narrowing Test")
    print("=" * 70)

    # -------------------------------------------------------------
    # Test Case 1: Standard Part (Medium Payload fitting Cartons)
    # -------------------------------------------------------------
    print("\n>>> TEST 1: Standard Stamping Bracket (Part Weight 1.2kg, SNP=4 -> 4.8kg)")
    req1 = {
        "name": "Stamping Bracket Standard",
        "part_length": 140.0,
        "part_width": 90.0,
        "part_height": 60.0,
        "part_weight": 1.2,
        "part_type": "steel",
        "snp": 4,
    }
    res1 = run_retrieval_gathering(req1)
    print(f"Tables Queried: {res1['tables_queried']}")
    print(f"Status: {res1['status']}")
    print(f"Summary: {res1['narrowing_summary']}")
    print(f"Total fitting in DB: {res1['total_candidates_found']} -> Narrowed to: {res1['narrowed_count']}")
    print("Top Narrowed Packages:")
    for pkg in res1["matching_packages"]:
        print(f"  [{pkg['rank']}] {pkg['name']} ({pkg['category_label']}) - {pkg['fit_tier']}")
        print(f"      Dims: {pkg['inner_dimensions_mm']['length']}x{pkg['inner_dimensions_mm']['width']}x{pkg['inner_dimensions_mm']['height']} mm")
        print(f"      Utilization: {pkg['volume_utilization_pct']}% | Wasted: {pkg['wasted_volume_liters']} L | Capacity: {pkg['max_weight_capacity_kg']} kg")

    # -------------------------------------------------------------
    # Test Case 2: Product auto-lookup from actual SQLite 'products' table
    # -------------------------------------------------------------
    print("\n>>> TEST 2: Product auto-lookup from SQLite 'products' table ('Steel Dowel Pin Small')")
    req2 = {
        "name": "Steel Dowel Pin Small",
    }
    res2 = run_retrieval_gathering(req2)
    print(f"Auto-resolved matched product ID: {res2['metrics'].get('matched_product_id')}")
    print(f"Resolved Dims: {res2['metrics']['single_product_dimensions_mm']} mm, SNP: {res2['metrics']['snp']}")
    print(f"Total fitting in DB: {res2['total_candidates_found']} -> Narrowed to: {res2['narrowed_count']}")
    print("Top Narrowed Packages:")
    for pkg in res2["matching_packages"]:
        print(f"  [{pkg['rank']}] {pkg['name']} - {pkg['fit_tier']} (Util: {pkg['volume_utilization_pct']}%)")

    # -------------------------------------------------------------
    # Test Case 3: Heavy Payload (> 9.0kg, e.g. 10.0kg Bracket or Solid Ingot)
    # -------------------------------------------------------------
    print("\n>>> TEST 3: Heavy Payload (10.0kg load exceeding 9kg carton capacity)")
    req3 = {
        "name": "Heavy Stamping Bracket Batch",
        "part_length": 140.0,
        "part_width": 90.0,
        "part_height": 60.0,
        "part_weight": 2.5,
        "part_type": "steel",
        "snp": 4,
    }
    res3 = run_retrieval_gathering(req3)
    print(f"Status: {res3['status']}")
    print(f"Summary: {res3['narrowing_summary']}")
    print(f"Narrowed Packages:")
    for pkg in res3["matching_packages"]:
        print(f"  [{pkg['rank']}] {pkg['name']} ({pkg['category_label']}) - {pkg['fit_tier']}")
        print(f"      Capacity: {pkg['max_weight_capacity_kg']} kg | Dims: {pkg['inner_dimensions_mm']['length']}x{pkg['inner_dimensions_mm']['width']}x{pkg['inner_dimensions_mm']['height']} mm")

    print("\n" + "=" * 70)
    print("All Retrieval & Gathering agent tests completed successfully!")
    print("=" * 70)
