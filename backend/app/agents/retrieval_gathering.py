"""Retrieval and Gathering Agent

A fully deterministic system that takes part/packaging requirements
(from the Requirement Gathering Agent or raw input specifications) and:
1. Calculates physical metrics:
   - max_rating (total payload rating = part_weight * snp)
   - single_product_volume (cm³ and liters)
   - total_product_volume (liters)
   - total_product_weight (kg)
   - fragility & padding rules based on material definition
   - multi-unit bounding box for SNP > 1
   - total volume and bounding box required including protective padding
2. Queries a 'packages' table in the database to fetch candidate packages that:
   - Physically fit the content dimensions (accounting for orthogonal 3D rotations)
   - Support the weight capacity (max_weight >= max_rating)
   - Have available stock (inventory > 0)
3. Evaluates and returns all fitting packages ranked by volume utilization.
"""

import os
import re
import sqlite3
from typing import TypedDict, List, Dict, Any, Optional, Union

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# Try importing domain helpers from services.custom_box, with resilient fallbacks
try:
    from app.services.custom_box.padding_rules import get_padding_for_part
except ImportError:
    def get_padding_for_part(part_type: str) -> Dict[str, Any]:
        target = (part_type or "").strip().lower()
        if any(k in target for k in ["glass", "ceramic", "fragile"]):
            return {"part_type": part_type, "recommended_padding": "epe_foam", "thickness_mm": 35.0, "fragility": "high"}
        if any(k in target for k in ["electronics", "pcb", "chip", "sensor"]):
            return {"part_type": part_type, "recommended_padding": "esd_anti_static_foam", "thickness_mm": 25.0, "fragility": "high"}
        if any(k in target for k in ["steel", "iron", "cast"]):
            return {"part_type": part_type, "recommended_padding": "dense_eva_foam", "thickness_mm": 20.0, "fragility": "medium"}
        if any(k in target for k in ["plastic", "poly"]):
            return {"part_type": part_type, "recommended_padding": "bubble_wrap", "thickness_mm": 12.0, "fragility": "low"}
        return {"part_type": part_type, "recommended_padding": "polyethylene_foam", "thickness_mm": 15.0, "fragility": "medium"}

try:
    from app.services.custom_box.multi_unit import calculate_multi_unit_layout
except ImportError:
    def calculate_multi_unit_layout(part_length: float, part_width: float, part_height: float, part_weight: float, quantity: int = 1) -> Dict[str, Any]:
        return {
            "quantity": quantity,
            "grid": {"nx": 1, "ny": quantity, "nz": 1},
            "content_dimensions_mm": {"length": part_length, "width": part_width * quantity, "height": part_height},
            "total_part_weight_kg": round(part_weight * quantity, 3),
            "divider_thickness_mm": 3.0,
            "alternative_layouts_count": 1,
        }

# Database path resolution
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "data", "products.db")
DB_PATH = os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH)


# Standard fallback packages used when packages table is not yet created in SQLite
STANDARD_FALLBACK_PACKAGES = [
    {"package_code": "BOX-S1", "name": "Small Standard Carton (S-1)", "length": 220.0, "width": 160.0, "height": 120.0, "max_weight_capacity": 6.0, "inventory": 150, "material": "Single Wall Cardboard"},
    {"package_code": "BOX-M1", "name": "Medium Standard Carton (M-1)", "length": 320.0, "width": 240.0, "height": 180.0, "max_weight_capacity": 15.0, "inventory": 85, "material": "Double Wall Cardboard"},
    {"package_code": "BOX-L1", "name": "Large Shipping Box (L-1)", "length": 450.0, "width": 350.0, "height": 250.0, "max_weight_capacity": 25.0, "inventory": 40, "material": "Double Wall Heavy Duty"},
    {"package_code": "BOX-XL1", "name": "Extra Large Cargo Box (XL-1)", "length": 600.0, "width": 450.0, "height": 350.0, "max_weight_capacity": 40.0, "inventory": 25, "material": "Triple Wall Industrial"},
    {"package_code": "BOX-TALL", "name": "Tall Column Carton (T-1)", "length": 250.0, "width": 250.0, "height": 600.0, "max_weight_capacity": 20.0, "inventory": 15, "material": "Heavy Duty Cardboard"},
    {"package_code": "BOX-LONG", "name": "Long Rail Tube Box (R-1)", "length": 1250.0, "width": 180.0, "height": 150.0, "max_weight_capacity": 30.0, "inventory": 10, "material": "Heavy Reinforced Cardboard"},
    {"package_code": "BOX-CRATE", "name": "Reinforced Wooden Crate (CR-1)", "length": 700.0, "width": 550.0, "height": 450.0, "max_weight_capacity": 100.0, "inventory": 8, "material": "Plywood / Pine Crate"},
    {"package_code": "BOX-OUTOFSTOCK", "name": "Out of Stock Carton (OOS-1)", "length": 500.0, "width": 500.0, "height": 500.0, "max_weight_capacity": 50.0, "inventory": 0, "material": "Cardboard"},
]


# ==========================================
# Schema Definitions
# ==========================================

class PartRequirements(BaseModel):
    name: str = Field(default="Part", description="Name of the part")
    description: Optional[str] = Field(default="", description="Detailed description")
    snp: Union[int, str] = Field(default=1, description="Standard Number of Packs (SNP)")
    part_length: float = Field(..., gt=0, description="Length in mm")
    part_width: float = Field(..., gt=0, description="Width in mm")
    part_height: float = Field(..., gt=0, description="Height in mm")
    part_type: str = Field(default="standard", description="Material definition (e.g. steel, aluminum, glass, plastic)")
    part_weight: float = Field(..., ge=0, description="Weight of single part in kg")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CalculatedProductMetrics(BaseModel):
    snp: int
    max_rating: float
    single_product_volume_cm3: float
    single_product_volume_liters: float
    total_product_volume_liters: float
    total_product_weight_kg: float
    fragility: str
    recommended_padding_material: str
    recommended_padding_thickness_mm: float
    content_dimensions_mm: Dict[str, float]
    effective_bounding_box_mm: Dict[str, float]
    total_volume_required_liters: float
    multi_unit_grid: Dict[str, int]


class PackageCandidate(BaseModel):
    package_id: Any
    package_code: str
    name: str
    length: float
    width: float
    height: float
    max_weight_capacity: float
    inventory: int
    volume_liters: float
    volume_utilization_pct: float
    wasted_volume_liters: float
    fits: bool
    material: Optional[str] = None


class RetrievalGatheringState(TypedDict, total=False):
    requirements: Dict[str, Any]
    metrics: Dict[str, Any]
    matching_packages: List[Dict[str, Any]]
    total_candidates_found: int
    packages_table_exists: bool
    status: str
    message: Optional[str]


# ==========================================
# Deterministic Calculation Engine
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


def calculate_metrics(requirements_input: Union[BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate deterministic physical metrics from input requirements."""
    if hasattr(requirements_input, "model_dump"):
        data = requirements_input.model_dump()
    elif isinstance(requirements_input, dict):
        data = dict(requirements_input)
    else:
        raise ValueError(f"Unsupported requirements type: {type(requirements_input)}")

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
    content_dims = multi_unit.get("content_dimensions_mm", {"length": length, "width": width, "height": height})
    grid = multi_unit.get("grid", {"nx": 1, "ny": 1, "nz": 1})

    # 5. Total Effective Dimensions (content + 2*padding on all 3 axes)
    eff_length = round(content_dims["length"] + (2 * padding_thickness), 2)
    eff_width = round(content_dims["width"] + (2 * padding_thickness), 2)
    eff_height = round(content_dims["height"] + (2 * padding_thickness), 2)

    total_volume_required_liters = round((eff_length * eff_width * eff_height) / 1000000.0, 4)

    return {
        "part_name": data.get("name") or data.get("part_name") or "Part",
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
# Package Query & Gathering Engine
# ==========================================

def _detect_column(column_names: List[str], candidates: List[str]) -> Optional[str]:
    """Find a column in a table matching any candidate name case-insensitively."""
    lower_map = {c.lower(): c for c in column_names}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def query_candidate_packages(
    metrics: Dict[str, Any],
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Query 'packages' table in SQLite database and filter by:
    1. inventory > 0
    2. 3D spatial fit (content dimensions + padding <= internal dimensions)
    3. max_weight_capacity >= max_rating
    """
    target_db = db_path or DB_PATH
    eff_dims = metrics["effective_bounding_box_mm"]
    req_l = eff_dims["length"]
    req_w = eff_dims["width"]
    req_h = eff_dims["height"]
    max_rating = metrics["max_rating"]
    vol_required = metrics["total_volume_required_liters"]

    packages_data: List[Dict[str, Any]] = []
    table_exists = False

    # Check database and table existence
    if os.path.exists(target_db):
        try:
            conn = sqlite3.connect(target_db)
            conn.row_factory = sqlite3.Row
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type IN ('table', 'view') AND LOWER(name) = 'packages'
                """)
                table_row = cursor.fetchone()

                if table_row:
                    table_exists = True
                    # Inspect column names to adapt to any table schema
                    cursor.execute("PRAGMA table_info(packages)")
                    col_info = cursor.fetchall()
                    col_names = [r[1] for r in col_info]

                    # Auto-detect column mappings
                    len_col = _detect_column(col_names, ["length", "internal_length", "length_mm", "internal_length_mm", "l"])
                    wid_col = _detect_column(col_names, ["width", "breadth", "internal_width", "width_mm", "internal_breadth_mm", "w"])
                    hei_col = _detect_column(col_names, ["height", "internal_height", "height_mm", "internal_height_mm", "h"])
                    wt_col = _detect_column(col_names, ["max_weight_capacity", "max_weight", "max_weight_kg", "capacity_kg", "weight_capacity"])
                    inv_col = _detect_column(col_names, ["inventory", "inventory_count", "stock_quantity", "quantity", "stock", "qty"])
                    code_col = _detect_column(col_names, ["package_code", "code", "package_id", "sku", "name", "id"])
                    name_col = _detect_column(col_names, ["name", "package_name", "description", "title", "package_code"])

                    # Fetch all package rows from table
                    cursor.execute("SELECT * FROM packages")
                    raw_rows = cursor.fetchall()

                    for r in raw_rows:
                        row_dict = dict(r)
                        pkg_len = float(row_dict[len_col]) if len_col and row_dict.get(len_col) is not None else 0.0
                        pkg_wid = float(row_dict[wid_col]) if wid_col and row_dict.get(wid_col) is not None else 0.0
                        pkg_hei = float(row_dict[hei_col]) if hei_col and row_dict.get(hei_col) is not None else 0.0
                        pkg_wt = float(row_dict[wt_col]) if wt_col and row_dict.get(wt_col) is not None else 9999.0
                        pkg_inv = int(row_dict[inv_col]) if inv_col and row_dict.get(inv_col) is not None else 1
                        pkg_code = str(row_dict.get(code_col, row_dict.get("id", "PKG")))
                        pkg_name = str(row_dict.get(name_col, pkg_code))

                        packages_data.append({
                            "package_id": row_dict.get("id", pkg_code),
                            "package_code": pkg_code,
                            "name": pkg_name,
                            "length": pkg_len,
                            "width": pkg_wid,
                            "height": pkg_hei,
                            "max_weight_capacity": pkg_wt,
                            "inventory": pkg_inv,
                            "material": row_dict.get("material", "Standard Packaging"),
                        })
            conn.close()
        except Exception:
            table_exists = False

    # If the user has not yet created the 'packages' table in the DB,
    # evaluate against the standard fallback packages so the agent is immediately usable.
    if not table_exists:
        packages_data = list(STANDARD_FALLBACK_PACKAGES)

    # -------------------------------------------------------------
    # Filtering:
    # 1. inventory > 0
    # 2. 3D fit (under any orthogonal rotation)
    # 3. max_weight_capacity >= max_rating
    # -------------------------------------------------------------
    matching_packages = []

    for pkg in packages_data:
        inventory = int(pkg.get("inventory", 0))

        # Check inventory > 0
        if inventory <= 0:
            continue

        box_l = float(pkg["length"])
        box_w = float(pkg["width"])
        box_h = float(pkg["height"])
        max_wt = float(pkg.get("max_weight_capacity", 9999.0))

        # Check 3D geometric fit
        fits_3d = check_3d_fits([req_l, req_w, req_h], [box_l, box_w, box_h])

        # Check weight capacity
        fits_weight = max_wt >= max_rating

        if fits_3d and fits_weight:
            box_volume_liters = round((box_l * box_w * box_h) / 1000000.0, 3)
            utilization_pct = round((vol_required / max(0.001, box_volume_liters)) * 100.0, 1)
            wasted_vol = round(max(0.0, box_volume_liters - vol_required), 3)

            matching_packages.append({
                "package_id": pkg.get("package_id", pkg.get("package_code")),
                "package_code": pkg.get("package_code", "PKG"),
                "name": pkg.get("name", "Standard Box"),
                "dimensions_mm": {"length": box_l, "width": box_w, "height": box_h},
                "max_weight_capacity_kg": max_wt,
                "inventory": inventory,
                "box_volume_liters": box_volume_liters,
                "volume_utilization_pct": min(100.0, utilization_pct),
                "wasted_volume_liters": wasted_vol,
                "material": pkg.get("material", "Cardboard"),
            })

    # Sort matching packages by volume utilization descending (best fit first)
    matching_packages.sort(key=lambda p: p["volume_utilization_pct"], reverse=True)

    return {
        "packages_table_exists": table_exists,
        "database_path": os.path.abspath(target_db),
        "matching_packages": matching_packages,
        "total_matching": len(matching_packages),
        "schema_hint": None if table_exists else "Table 'packages' not found in database. Evaluated against standard fallback packages. You can create 'packages' table anytime.",
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
    """Node 2: Query packages table, filter by inventory > 0, 3D fit, and weight."""
    metrics = state.get("metrics", {})
    query_result = query_candidate_packages(metrics)

    packages = query_result["matching_packages"]
    table_exists = query_result["packages_table_exists"]

    status = "packages_found" if packages else "no_fitting_package_in_stock"
    message = (
        f"Found {len(packages)} fitting package(s) with available inventory."
        if packages
        else "No package in inventory can fit the required bounding box and weight."
    )

    if not table_exists:
        message += " (Note: 'packages' table not yet present in SQLite; evaluated against standard package models)."

    return {
        "matching_packages": packages,
        "total_candidates_found": len(packages),
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
) -> Dict[str, Any]:
    """Standalone entrypoint to run the Retrieval & Gathering agent directly."""
    req_dict = requirements.model_dump() if hasattr(requirements, "model_dump") else dict(requirements)

    metrics = calculate_metrics(req_dict)
    query_result = query_candidate_packages(metrics, db_path=db_path)

    packages = query_result["matching_packages"]
    status = "packages_found" if packages else "no_fitting_package_in_stock"

    return {
        "requirements": req_dict,
        "metrics": metrics,
        "matching_packages": packages,
        "total_candidates_found": len(packages),
        "packages_table_exists": query_result["packages_table_exists"],
        "status": status,
        "schema_hint": query_result.get("schema_hint"),
    }


# ==========================================
# Standalone CLI Self-Test
# ==========================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Retrieval & Gathering Agent (Standalone)")
    print("=" * 60)

    sample_requirement = {
        "name": "Heavy Stamping Bracket",
        "part_length": 140.0,
        "part_width": 90.0,
        "part_height": 60.0,
        "part_weight": 2.5,
        "part_type": "steel",
        "snp": 4,
    }

    result = run_retrieval_gathering(sample_requirement)

    print("\n--- 1. CALCULATED METRICS ---")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")

    print("\n--- 2. MATCHING PACKAGES (Inventory > 0 & 3D Fits) ---")
    print(f"Total Fitting Packages Found: {result['total_candidates_found']}")
    for idx, pkg in enumerate(result["matching_packages"], 1):
        print(f"  [{idx}] {pkg['name']} ({pkg['package_code']})")
        print(f"      Dimensions: {pkg['dimensions_mm']['length']}x{pkg['dimensions_mm']['width']}x{pkg['dimensions_mm']['height']} mm")
        print(f"      Capacity: {pkg['max_weight_capacity_kg']} kg (Required: {result['metrics']['max_rating']} kg)")
        print(f"      Inventory Stock: {pkg['inventory']} units")
        print(f"      Volume Utilization: {pkg['volume_utilization_pct']}% (Wasted: {pkg['wasted_volume_liters']} L)")

    if result.get("schema_hint"):
        print(f"\nInfo: {result['schema_hint']}")

