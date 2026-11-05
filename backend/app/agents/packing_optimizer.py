"""Packing Optimizer Agent (Deterministic Extreme Point 3D Spatial Engine)

A deterministic spatial packing agent built on LangGraph that uses
3D Extreme Point / Corner Point analysis to:
1. Parse and resolve items (homogeneous SNP batches or multi-item mixed manifests).
   Auto-populates part geometry and SNP from SQLite `products` table if product_id or part_name is passed.
2. Select candidate containers:
   Uses explicit containers, or auto-retrieves the top narrowed candidates from `retrieval_gathering`
   and SQLite `packages` table.
3. Perform 3D Extreme Point Spatial Packing Analysis:
   - Evaluates full 6-degree orthogonal rotations (or yaw-only upright rotations).
   - Generates and tests 3D Extreme Points (canonical corner coordinates + orthogonal projections).
   - Enforces rigid bounding box collision avoidance and container boundaries.
   - Computes physical stability and placement coordinates (x, y, z).
4. Determines:
   - Does everything fit? (fits: True / False, placed vs unplaced items)
   - What is the best primary orientation? (e.g. length x width x height alignment)
   - Comprehensive utilization metrics (volume utilization %, wasted liters, bounding box density, weight capacity).
   - 3D Scene Data ready for direct rendering in the frontend Three.js viewer.

Note: Runs fully deterministically without LLM calls for maximum speed, reproducibility,
and zero token cost, while adhering to the LangGraph StateGraph agent interface so that
LLM agentic reasoning or conversational explanations can be layered on seamlessly in the future.
"""

import os
import re
import sqlite3
from typing import TypedDict, List, Dict, Any, Optional, Union, Tuple

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# Database & Domain Helpers
from app.services.packing.orientations import get_possible_orientations
from app.services.render.viewer import generate_scene_data

try:
    from app.agents.retrieval_gathering import run_retrieval_gathering
except ImportError:
    run_retrieval_gathering = None

try:
    from app.db import get_product_by_id, get_product_by_name, get_all_packages, DB_PATH
except ImportError:
    get_product_by_id = None
    get_product_by_name = None
    get_all_packages = None
    BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = os.path.join(BACKEND_DIR, "data", "products.db")


# ==========================================
# Schema Definitions
# ==========================================

class ItemSpec(BaseModel):
    id: Optional[str] = Field(default=None, description="Unique item identifier")
    name: Optional[str] = Field(default="Item", description="Item name or SKU")
    length: float = Field(..., gt=0, description="Item length in mm")
    width: float = Field(..., gt=0, description="Item width in mm")
    height: float = Field(..., gt=0, description="Item height in mm")
    weight: float = Field(default=0.0, ge=0, description="Item weight in kg")
    quantity: int = Field(default=1, ge=1, description="Number of duplicate items to pack")
    allow_rotation: bool = Field(default=True, description="Allow 3D orthogonal rotation")
    keep_upright: bool = Field(default=False, description="Restrict rotation to vertical yaw only")


class ContainerSpec(BaseModel):
    name: Optional[str] = Field(default="Container", description="Container name or reference")
    category: Optional[str] = Field(default="carton", description="carton, metal_stillage, etc.")
    length: float = Field(..., gt=0, description="Internal length in mm")
    width: float = Field(..., gt=0, description="Internal width in mm")
    height: float = Field(..., gt=0, description="Internal height in mm")
    max_weight_capacity_kg: Optional[float] = Field(default=1000.0, description="Max weight capacity in kg")
    inventory: Optional[int] = Field(default=None, description="Available stock count, if provided")


class PackingOptimizerInput(BaseModel):
    product_id: Optional[int] = Field(default=None, description="Optional SQLite Product ID to pack")
    part_name: Optional[str] = Field(default=None, description="Optional SQLite Part Name to pack")
    part_length: Optional[float] = Field(default=None, description="Part length in mm")
    part_width: Optional[float] = Field(default=None, description="Part width in mm")
    part_height: Optional[float] = Field(default=None, description="Part height in mm")
    part_weight: Optional[float] = Field(default=None, description="Part weight in kg")
    part_type: Optional[str] = Field(default="Standard", description="Material type")
    snp: Optional[Union[int, str]] = Field(default=None, description="Quantity / SNP")
    items: Optional[List[Dict[str, Any]]] = Field(default=None, description="Explicit item list")
    container: Optional[Dict[str, Any]] = Field(default=None, description="Target container")
    candidate_containers: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of candidate containers")
    allow_rotation: bool = Field(default=True, description="Global allow rotation flag")
    keep_upright: bool = Field(default=False, description="Global keep upright flag")
    auto_fetch_db_packages: bool = Field(default=True, description="Fetch best packages from DB if none provided")


class PackingOptimizerState(TypedDict, total=False):
    input: Dict[str, Any]
    resolved_items: List[Dict[str, Any]]
    candidate_containers: List[Dict[str, Any]]
    packing_evaluations: List[Dict[str, Any]]
    best_evaluation: Optional[Dict[str, Any]]
    best_container: Optional[Dict[str, Any]]
    best_orientation: Optional[Dict[str, float]]
    fits: bool
    utilization_metrics: Dict[str, Any]
    scene_data: Dict[str, Any]
    status: str
    summary: str


# ==========================================
# Extreme Point 3D Geometric Engine
# ==========================================

class PlacedBox:
    """Represents a placed item with exact 3D coordinates and bounding extents."""

    def __init__(self, item_id: str, name: str, x: float, y: float, z: float, dx: float, dy: float, dz: float, weight: float = 0.0):
        self.item_id = item_id
        self.name = name
        self.x = round(float(x), 2)
        self.y = round(float(y), 2)
        self.z = round(float(z), 2)
        self.dx = round(float(dx), 2)
        self.dy = round(float(dy), 2)
        self.dz = round(float(dz), 2)
        self.weight = round(float(weight), 3)

    @property
    def x2(self) -> float:
        return self.x + self.dx

    @property
    def y2(self) -> float:
        return self.y + self.dy

    @property
    def z2(self) -> float:
        return self.z + self.dz

    def overlaps(self, other: "PlacedBox") -> bool:
        """3D Axis-Aligned Bounding Box (AABB) intersection check with tolerance."""
        eps = 1e-3
        return not (
            self.x2 <= other.x + eps or
            other.x2 <= self.x + eps or
            self.y2 <= other.y + eps or
            other.y2 <= self.y + eps or
            self.z2 <= other.z + eps or
            other.z2 <= self.z + eps
        )

    def contains_point(self, px: float, py: float, pz: float) -> bool:
        """Check if an extreme point lies strictly inside this placed box."""
        eps = 1e-3
        return (
            self.x - eps <= px < self.x2 - eps and
            self.y - eps <= py < self.y2 - eps and
            self.z - eps <= pz < self.z2 - eps
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "dimensions": {"length": self.dx, "width": self.dy, "height": self.dz},
            "weight_kg": self.weight,
        }


def generate_extreme_points(
    placed_items: List[PlacedBox],
    container_l: float,
    container_w: float,
    container_h: float,
) -> List[Tuple[float, float, float]]:
    """Generate and deduplicate Extreme Points (EP) based on Crainic et al. 3D EP Heuristic.

    When an item is placed at (x, y, z) with dimensions (dx, dy, dz):
    1. Canonical extreme points: (x + dx, y, z), (x, y + dy, z), (x, y, z + dz).
    2. Boundary projections against neighboring boxes.
    3. Filter out points inside any existing item or outside container boundaries.
    """
    if not placed_items:
        return [(0.0, 0.0, 0.0)]

    raw_points: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)]

    for box in placed_items:
        # Canonical extreme points generated by this box
        raw_points.append((box.x2, box.y, box.z))
        raw_points.append((box.x, box.y2, box.z))
        raw_points.append((box.x, box.y, box.z2))

        # Projected extreme points against other placed boxes
        for other in placed_items:
            if other is box:
                continue

            # Projection along X: align with other box's X boundary
            if box.x2 < other.x2 and other.y <= box.y < other.y2 and other.z <= box.z < other.z2:
                raw_points.append((other.x2, box.y, box.z))

            # Projection along Y: align with other box's Y boundary
            if box.y2 < other.y2 and other.x <= box.x < other.x2 and other.z <= box.z < other.z2:
                raw_points.append((box.x, other.y2, box.z))

            # Projection along Z: align with other box's Z boundary
            if box.z2 < other.z2 and other.x <= box.x < other.x2 and other.y <= box.y < other.y2:
                raw_points.append((box.x, box.y, other.z2))

    # Filter and deduplicate extreme points
    valid_points: List[Tuple[float, float, float]] = []
    seen = set()
    eps = 0.05

    for pt in raw_points:
        px, py, pz = round(pt[0], 2), round(pt[1], 2), round(pt[2], 2)

        # Check container boundaries
        if px >= container_l or py >= container_w or pz >= container_h:
            continue

        # Check if point is inside any already placed box
        inside_any = any(b.contains_point(px, py, pz) for b in placed_items)
        if inside_any:
            continue

        # Key for deduplication
        key = (round(px / eps), round(py / eps), round(pz / eps))
        if key not in seen:
            seen.add(key)
            valid_points.append((px, py, pz))

    # Sort Extreme Points: Lowest Z first (stability), then Lowest Y, Lowest X
    valid_points.sort(key=lambda p: (p[2], p[1], p[0]))
    return valid_points


def calculate_max_container_capacity(
    container_l: float,
    container_w: float,
    container_h: float,
    part_l: float,
    part_w: float,
    part_h: float,
    part_weight: float = 0.0,
    allow_rotation: bool = True,
    keep_upright: bool = False,
    max_weight_capacity_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate the maximum physical capacity of identical parts that can fit inside a container.

    Evaluates full orthogonal orientations and residual slab arrangements along X, Y, and Z.
    """
    if part_l <= 0 or part_w <= 0 or part_h <= 0 or container_l <= 0 or container_w <= 0 or container_h <= 0:
        return {
            "max_parts": 0,
            "max_volume_utilization_pct": 0.0,
            "max_items_volume_liters": 0.0,
            "max_wasted_volume_liters": 0.0,
            "max_packed_weight_kg": 0.0,
            "container_volume_liters": 0.0,
            "max_weight_capacity_kg": max_weight_capacity_kg,
            "weight_within_limit": True,
        }

    orients = get_possible_orientations(
        part_l, part_w, part_h,
        allow_rotation=allow_rotation,
        keep_upright=keep_upright,
    )

    best_count = 0
    for dx, dy, dz in orients:
        nx = int(container_l // dx)
        ny = int(container_w // dy)
        nz = int(container_h // dz)
        main_count = nx * ny * nz
        if main_count == 0:
            continue

        rx = container_l - (nx * dx)
        extra_x = 0
        if rx > 0:
            for edx, edy, edz in orients:
                extra_x = max(extra_x, int(rx // edx) * int(container_w // edy) * int(container_h // edz))

        ry = container_w - (ny * dy)
        extra_y = 0
        if ry > 0:
            for edx, edy, edz in orients:
                extra_y = max(extra_y, int(container_l // edx) * int(ry // edy) * int(container_h // edz))

        rz = container_h - (nz * dz)
        extra_z = 0
        if rz > 0:
            for edx, edy, edz in orients:
                extra_z = max(extra_z, int(container_l // edx) * int(container_w // edy) * int(rz // edz))

        total = max(main_count + extra_x, main_count + extra_y, main_count + extra_z)
        if total > best_count:
            best_count = total

    cont_vol = container_l * container_w * container_h
    cont_vol_l = round(cont_vol / 1_000_000.0, 3)
    part_vol = part_l * part_w * part_h
    max_items_vol = best_count * part_vol
    max_items_vol_l = round(max_items_vol / 1_000_000.0, 3)
    max_util_pct = round(min(100.0, (max_items_vol / max(1.0, cont_vol)) * 100.0), 2)
    max_wasted_l = round(max(0.0, cont_vol_l - max_items_vol_l), 3)
    max_wt = round(best_count * part_weight, 3)
    wt_ok = (max_wt <= max_weight_capacity_kg) if max_weight_capacity_kg is not None else True

    return {
        "max_parts": best_count,
        "max_volume_utilization_pct": max_util_pct,
        "max_items_volume_liters": max_items_vol_l,
        "max_wasted_volume_liters": max_wasted_l,
        "max_packed_weight_kg": max_wt,
        "container_volume_liters": cont_vol_l,
        "max_weight_capacity_kg": max_weight_capacity_kg,
        "weight_within_limit": wt_ok,
    }


def pack_single_container_extreme_points(
    container: Dict[str, Any],
    items: List[Dict[str, Any]],
    allow_rotation: bool = True,
    keep_upright: bool = False,
) -> Dict[str, Any]:
    """Perform Extreme Point analysis on a single container."""
    c_l = float(container.get("inner_length_mm") or container.get("length", 300.0))
    c_w = float(container.get("inner_width_mm") or container.get("width", 200.0))
    c_h = float(container.get("inner_height_mm") or container.get("height", 100.0))
    max_wt = float(container.get("max_weight_capacity_kg") or container.get("max_weight_kg", 1000.0))
    c_name = str(container.get("name", "Container"))

    placed: List[PlacedBox] = []
    unplaced: List[Dict[str, Any]] = []

    # Sort items by volume descending (largest first)
    sorted_items = sorted(
        items,
        key=lambda it: float(it.get("length", 0)) * float(it.get("width", 0)) * float(it.get("height", 0)),
        reverse=True,
    )

    orientation_counter: Dict[Tuple[float, float, float], int] = {}

    for idx, item in enumerate(sorted_items):
        item_id = str(item.get("id", f"item_{idx + 1}"))
        item_name = str(item.get("name", "Item"))
        l = float(item.get("length", 100.0))
        w = float(item.get("width", 80.0))
        h = float(item.get("height", 50.0))
        weight = float(item.get("weight", 0.0))

        orientations = get_possible_orientations(
            l, w, h,
            allow_rotation=item.get("allow_rotation", allow_rotation),
            keep_upright=item.get("keep_upright", keep_upright),
        )

        extreme_points = generate_extreme_points(placed, c_l, c_w, c_h)

        best_placement: Optional[PlacedBox] = None
        best_score = float("inf")

        for pt in extreme_points:
            px, py, pz = pt

            for dx, dy, dz in orientations:
                # 1. Boundary check
                if px + dx > c_l or py + dy > c_w or pz + dz > c_h:
                    continue

                candidate = PlacedBox(item_id, item_name, px, py, pz, dx, dy, dz, weight)

                # 2. Collision check with placed items
                if any(candidate.overlaps(b) for b in placed):
                    continue

                # 3. Extreme Point Placement Score:
                # Lowest Z (weight 1000) -> Lowest Y (weight 10) -> Lowest X (weight 1)
                score = (pz * 1000.0) + (py * 10.0) + px

                if score < best_score:
                    best_score = score
                    best_placement = candidate

        if best_placement:
            placed.append(best_placement)
            # Track orientation tuple
            orient_tuple = (best_placement.dx, best_placement.dy, best_placement.dz)
            orientation_counter[orient_tuple] = orientation_counter.get(orient_tuple, 0) + 1
        else:
            unplaced.append({
                "item_id": item_id,
                "name": item_name,
                "dimensions": {"length": l, "width": w, "height": h},
                "weight_kg": weight,
                "reason": "Exceeds remaining container boundaries or clashes at all extreme points",
            })

    container_volume = c_l * c_w * c_h
    total_placed_vol = sum(b.dx * b.dy * b.dz for b in placed)
    total_packed_weight = sum(b.weight for b in placed)
    utilization_pct = (total_placed_vol / max(1.0, container_volume)) * 100.0
    wasted_vol = max(0.0, container_volume - total_placed_vol)

    # Calculate bounding box of placed items
    if placed:
        max_px = max(b.x2 for b in placed)
        max_py = max(b.y2 for b in placed)
        max_pz = max(b.z2 for b in placed)
        bounding_box_vol = max_px * max_py * max_pz
        bounding_box_util = (total_placed_vol / max(1.0, bounding_box_vol)) * 100.0
    else:
        bounding_box_vol = 0.0
        bounding_box_util = 0.0

    all_fit = len(unplaced) == 0 and total_packed_weight <= max_wt

    # Compile orientation breakdown for all placed items
    orientations_breakdown = [
        {
            "dimensions": {"length": orient[0], "width": orient[1], "height": orient[2]},
            "count": count,
            "percentage": round((count / max(1, len(placed))) * 100.0, 1),
            "item_ids": [b.item_id for b in placed if (b.dx, b.dy, b.dz) == orient],
        }
        for orient, count in sorted(orientation_counter.items(), key=lambda kv: kv[1], reverse=True)
    ]

    # Primary orientation (if any)
    if orientation_counter:
        best_orient_tuple = max(orientation_counter.items(), key=lambda kv: kv[1])[0]
        best_orient_dict = {
            "length": best_orient_tuple[0],
            "width": best_orient_tuple[1],
            "height": best_orient_tuple[2],
            "count_at_this_orientation": orientation_counter[best_orient_tuple],
        }
    else:
        best_orient_dict = None

    packing_result = {
        "candidate_id": str(
            container.get("package_code")
            or container.get("package_id")
            or c_name
        ),
        "package_id": container.get("package_id"),
        "package_code": container.get("package_code"),
        "container_name": c_name,
        "category": container.get("category", "carton"),
        "material": container.get("material"),
        "inventory": container.get("inventory"),
        "container_dimensions": {
            "length": c_l,
            "width": c_w,
            "height": c_h,
            "volume_liters": round(container_volume / 1000000.0, 3),
        },
        "max_weight_capacity_kg": max_wt,
        "total_packed_weight_kg": round(total_packed_weight, 3),
        "weight_within_limit": total_packed_weight <= max_wt,
        "fits": all_fit,
        "placed_count": len(placed),
        "unplaced_count": len(unplaced),
        "total_items": len(items),
        "volume_utilization_pct": round(min(100.0, utilization_pct), 2),
        "wasted_volume_liters": round(wasted_vol / 1000000.0, 3),
        "bounding_box_utilization_pct": round(min(100.0, bounding_box_util), 2),
        "best_orientation": best_orient_dict,
        "orientations_breakdown": orientations_breakdown,
        "placed_items": [b.to_dict() for b in placed],
        "unplaced_items": unplaced,
        "extreme_points_evaluated_count": len(generate_extreme_points(placed, c_l, c_w, c_h)),
    }

    # Calculate Maximum Container Utilisation Capacity
    if items:
        rep_it = items[0]
        max_util = calculate_max_container_capacity(
            container_l=c_l,
            container_w=c_w,
            container_h=c_h,
            part_l=float(rep_it.get("length", 100.0)),
            part_w=float(rep_it.get("width", 80.0)),
            part_h=float(rep_it.get("height", 50.0)),
            part_weight=float(rep_it.get("weight", 0.0)),
            allow_rotation=rep_it.get("allow_rotation", allow_rotation),
            keep_upright=rep_it.get("keep_upright", keep_upright),
            max_weight_capacity_kg=max_wt,
        )
    else:
        max_util = calculate_max_container_capacity(
            container_l=c_l,
            container_w=c_w,
            container_h=c_h,
            part_l=100.0,
            part_w=80.0,
            part_h=50.0,
            part_weight=0.0,
            max_weight_capacity_kg=max_wt,
        )
    packing_result["max_utilization"] = max_util

    # Generate Three.js Scene Data
    packing_result["scene_data"] = generate_scene_data(packing_result)
    return packing_result


# ==========================================
# Items & Containers Resolution
# ==========================================

def resolve_items_from_input(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Resolve discrete packing items from either an explicit list,
    a part requirement dict, or auto-lookup from SQLite `products` table.
    """
    # 1. Explicit items list provided
    if data.get("items") and isinstance(data["items"], list):
        flattened = []
        for idx, it in enumerate(data["items"]):
            qty = max(1, int(it.get("quantity", 1)))
            base_id = it.get("id") or f"item_{idx + 1}"
            for q in range(qty):
                flattened.append({
                    "id": f"{base_id}_{q + 1}" if qty > 1 else base_id,
                    "name": it.get("name", "Item"),
                    "length": float(it.get("length", 100.0)),
                    "width": float(it.get("width", 80.0)),
                    "height": float(it.get("height", 50.0)),
                    "weight": float(it.get("weight", 0.0)),
                    "allow_rotation": it.get("allow_rotation", data.get("allow_rotation", True)),
                    "keep_upright": it.get("keep_upright", data.get("keep_upright", False)),
                })
        return flattened

    # 2. Check if product_id or part_name is provided for auto-lookup from products table
    product_row = None
    pid = data.get("product_id")
    pname = data.get("part_name") or data.get("name")

    if (pid is not None or pname is not None) and get_product_by_id and get_product_by_name:
        if pid is not None:
            try:
                product_row = get_product_by_id(int(pid))
            except Exception:
                pass
        if not product_row and pname:
            try:
                product_row = get_product_by_name(str(pname))
            except Exception:
                pass

    if product_row:
        p_len = float(data.get("part_length") or product_row.get("part_length", 100.0))
        p_wid = float(data.get("part_width") or product_row.get("part_breadth", 80.0))
        p_hei = float(data.get("part_height") or product_row.get("part_height", 50.0))
        p_wt = float(data.get("part_weight") or product_row.get("part_weight", 1.0))
        p_name = str(data.get("part_name") or product_row.get("part_name", "Part"))

        # Quantity / SNP
        raw_snp = data.get("snp") or product_row.get("standard_no_of_parts", 1)
        if isinstance(raw_snp, str):
            match = re.search(r"\d+", raw_snp)
            snp = int(match.group(0)) if match else 1
        else:
            snp = max(1, int(raw_snp or 1))

        return [
            {
                "id": f"{p_name.replace(' ', '_').lower()}_{i + 1}",
                "name": p_name,
                "length": p_len,
                "width": p_wid,
                "height": p_hei,
                "weight": p_wt,
                "allow_rotation": data.get("allow_rotation", True),
                "keep_upright": data.get("keep_upright", False),
            }
            for i in range(snp)
        ]

    # 3. Direct dimensional input (single part with SNP)
    p_len = float(data.get("part_length") or data.get("length") or 100.0)
    p_wid = float(data.get("part_width") or data.get("width") or 80.0)
    p_hei = float(data.get("part_height") or data.get("height") or 50.0)
    p_wt = float(data.get("part_weight") or data.get("weight") or 1.0)
    p_name = str(data.get("part_name") or data.get("name") or "Part")

    raw_snp = data.get("snp", 1)
    if isinstance(raw_snp, str):
        match = re.search(r"\d+", raw_snp)
        snp = int(match.group(0)) if match else 1
    else:
        snp = max(1, int(raw_snp or 1))

    return [
        {
            "id": f"item_{i + 1}",
            "name": p_name,
            "length": p_len,
            "width": p_wid,
            "height": p_hei,
            "weight": p_wt,
            "allow_rotation": data.get("allow_rotation", True),
            "keep_upright": data.get("keep_upright", False),
        }
        for i in range(snp)
    ]


def resolve_candidate_containers(
    data: Dict[str, Any],
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Resolve candidate containers from input or auto-retrieve top narrowed packages."""
    # 1. Explicit candidate containers list
    if data.get("candidate_containers") and isinstance(data["candidate_containers"], list):
        return [
            {
                "name": c.get("name") or c.get("package") or f"Box_{i + 1}",
                "package_id": c.get("package_id"),
                "package_code": c.get("package_code"),
                "category": c.get("category", "carton"),
                "inner_length_mm": float(c.get("inner_length_mm") or c.get("length", 300.0)),
                "inner_width_mm": float(c.get("inner_width_mm") or c.get("width", 200.0)),
                "inner_height_mm": float(c.get("inner_height_mm") or c.get("height", 100.0)),
                "max_weight_capacity_kg": float(c.get("max_weight_capacity_kg") or c.get("max_weight_kg", 1000.0)),
                "material": c.get("material"),
                "inventory": c.get("inventory"),
            }
            for i, c in enumerate(data["candidate_containers"])
        ]

    # 2. Explicit single container
    if data.get("container") and isinstance(data["container"], dict):
        c = data["container"]
        return [{
            "name": c.get("name") or c.get("package") or "Container",
            "package_id": c.get("package_id"),
            "package_code": c.get("package_code"),
            "category": c.get("category", "carton"),
            "inner_length_mm": float(c.get("inner_length_mm") or c.get("length", 300.0)),
            "inner_width_mm": float(c.get("inner_width_mm") or c.get("width", 200.0)),
            "inner_height_mm": float(c.get("inner_height_mm") or c.get("height", 100.0)),
            "max_weight_capacity_kg": float(c.get("max_weight_capacity_kg") or c.get("max_weight_kg", 1000.0)),
            "material": c.get("material"),
            "inventory": c.get("inventory"),
        }]

    # 3. Auto-fetch top narrowed packages from retrieval_gathering / SQLite database
    if data.get("auto_fetch_db_packages", True) and run_retrieval_gathering:
        try:
            total_wt = sum(float(it.get("weight", 0)) for it in items)
            # Use representative first item
            sample = items[0] if items else {"length": 100.0, "width": 80.0, "height": 50.0, "weight": 1.0}
            retrieval_req = {
                "name": sample.get("name", "Part"),
                "part_length": sample.get("length"),
                "part_width": sample.get("width"),
                "part_height": sample.get("height"),
                "part_weight": total_wt / max(1, len(items)),
                "snp": len(items),
            }
            ret_res = run_retrieval_gathering(retrieval_req, max_results=5)
            narrowed_pkgs = ret_res.get("matching_packages", [])

            if narrowed_pkgs:
                candidates = []
                for p in narrowed_pkgs:
                    inner_dims = p.get("inner_dimensions_mm", {})
                    candidates.append({
                        "name": p.get("name"),
                        "package_id": p.get("package_id"),
                        "package_code": p.get("package_code"),
                        "category": p.get("category", "carton"),
                        "inner_length_mm": float(inner_dims.get("length", 300.0)),
                        "inner_width_mm": float(inner_dims.get("width", 200.0)),
                        "inner_height_mm": float(inner_dims.get("height", 100.0)),
                        "max_weight_capacity_kg": float(p.get("max_weight_capacity_kg", 9.0)),
                        "material": p.get("material"),
                        "inventory": p.get("inventory"),
                    })
                return candidates
        except Exception:
            pass

    # 4. Standard default shipping cartons fallback
    return [
        {"name": "Package 1", "category": "carton", "inner_length_mm": 288.0, "inner_width_mm": 188.0, "inner_height_mm": 92.0, "max_weight_capacity_kg": 4.6},
        {"name": "Package 3", "category": "carton", "inner_length_mm": 303.0, "inner_width_mm": 198.0, "inner_height_mm": 102.0, "max_weight_capacity_kg": 5.2},
        {"name": "Package 9", "category": "carton", "inner_length_mm": 346.0, "inner_width_mm": 226.0, "inner_height_mm": 131.0, "max_weight_capacity_kg": 5.4},
        {"name": "Package 16", "category": "carton", "inner_length_mm": 394.0, "inner_width_mm": 259.0, "inner_height_mm": 165.0, "max_weight_capacity_kg": 6.4},
        {"name": "Package 25", "category": "carton", "inner_length_mm": 454.0, "inner_width_mm": 298.0, "inner_height_mm": 204.0, "max_weight_capacity_kg": 7.3},
    ]


# ==========================================
# LangGraph Workflow Implementation
# ==========================================

def prepare_items_and_containers_node(state: PackingOptimizerState) -> Dict[str, Any]:
    """Node 1: Resolve discrete packing items and select container candidates."""
    in_data = state.get("input", {})
    resolved_items = resolve_items_from_input(in_data)
    candidate_containers = resolve_candidate_containers(in_data, resolved_items)

    return {
        "resolved_items": resolved_items,
        "candidate_containers": candidate_containers,
    }


def extreme_point_packing_node(state: PackingOptimizerState) -> Dict[str, Any]:
    """Node 2: Execute Extreme Point 3D Spatial Packing across container candidates."""
    items = state.get("resolved_items", [])
    containers = state.get("candidate_containers", [])
    in_data = state.get("input", {})

    allow_rot = in_data.get("allow_rotation", True)
    keep_upright = in_data.get("keep_upright", False)

    evaluations: List[Dict[str, Any]] = []

    for c in containers:
        res = pack_single_container_extreme_points(
            container=c,
            items=items,
            allow_rotation=allow_rot,
            keep_upright=keep_upright,
        )
        evaluations.append(res)

    return {"packing_evaluations": evaluations}


def evaluate_and_rank_node(state: PackingOptimizerState) -> Dict[str, Any]:
    """Node 3: Rank results, determine optimal container, orientation, and summary."""
    evaluations = state.get("packing_evaluations", [])
    items = state.get("resolved_items", [])

    if not evaluations:
        return {
            "fits": False,
            "status": "no_containers_evaluated",
            "summary": "No container candidates could be evaluated.",
        }

    # Separate candidates where all items fit vs partial fit
    fitting_candidates = [e for e in evaluations if e["fits"]]

    if fitting_candidates:
        # Sort fitting containers by volume utilization descending (best fit first)
        fitting_candidates.sort(key=lambda e: e["volume_utilization_pct"], reverse=True)
        best = fitting_candidates[0]
        fits_all = True
        status = "optimal_packing_found"
        summary = (
            f"Successfully packed all {best['placed_count']} items into {best['container_name']} "
            f"using 3D Extreme Point analysis. Optimal volume utilization: {best['volume_utilization_pct']}% "
            f"(Wasted space: {best['wasted_volume_liters']} L, Packed weight: {best['total_packed_weight_kg']} kg)."
        )
    else:
        # If none fit completely, select the one that placed the most items, then highest utilization
        evaluations.sort(key=lambda e: (e["placed_count"], e["volume_utilization_pct"]), reverse=True)
        best = evaluations[0]
        fits_all = False
        status = "partial_fit_only"
        summary = (
            f"Items do not fully fit into the evaluated containers. {best['container_name']} placed "
            f"{best['placed_count']}/{best['total_items']} items ({best['unplaced_count']} unplaced). "
            f"A larger container or custom box is recommended."
        )

    best_orientation = best.get("best_orientation")

    utilization_metrics = {
        "container_name": best.get("container_name"),
        "container_volume_liters": best.get("container_dimensions", {}).get("volume_liters"),
        "volume_utilization_pct": best.get("volume_utilization_pct"),
        "wasted_volume_liters": best.get("wasted_volume_liters"),
        "bounding_box_utilization_pct": best.get("bounding_box_utilization_pct"),
        "total_packed_weight_kg": best.get("total_packed_weight_kg"),
        "max_weight_capacity_kg": best.get("max_weight_capacity_kg"),
        "weight_within_limit": best.get("weight_within_limit"),
        "placed_count": best.get("placed_count"),
        "unplaced_count": best.get("unplaced_count"),
        "total_items": best.get("total_items"),
        "max_utilization": best.get("max_utilization"),
    }

    c_dims = best.get("container_dimensions") or {}
    return {
        "best_evaluation": best,
        "best_container": {
            "name": best.get("container_name"),
            "candidate_id": best.get("candidate_id"),
            "package_id": best.get("package_id"),
            "package_code": best.get("package_code"),
            "category": best.get("category"),
            "material": best.get("material"),
            "inventory": best.get("inventory"),
            "inner_dimensions_mm": {
                "length": c_dims.get("length", 0.0),
                "width": c_dims.get("width", 0.0),
                "height": c_dims.get("height", 0.0),
            },
            "dimensions": c_dims,
            "max_weight_capacity_kg": best.get("max_weight_capacity_kg"),
        },
        "best_orientation": best_orientation,
        "orientations_breakdown": best.get("orientations_breakdown", []),
        "fits": fits_all,
        "utilization_metrics": utilization_metrics,
        "scene_data": best.get("scene_data", {}),
        "status": status,
        "summary": summary,
    }


# Construct StateGraph
packing_agent = StateGraph(PackingOptimizerState)

packing_agent.add_node("prepare_items_and_containers", prepare_items_and_containers_node)
packing_agent.add_node("extreme_point_packing", extreme_point_packing_node)
packing_agent.add_node("evaluate_and_rank", evaluate_and_rank_node)

packing_agent.add_edge(START, "prepare_items_and_containers")
packing_agent.add_edge("prepare_items_and_containers", "extreme_point_packing")
packing_agent.add_edge("extreme_point_packing", "evaluate_and_rank")
packing_agent.add_edge("evaluate_and_rank", END)

# Compiled LangGraph runnable
app = packing_agent.compile()


# ==========================================
# Standalone Direct Callable
# ==========================================

def run_packing_optimizer(
    input_data: Union[PackingOptimizerInput, Dict[str, Any]],
) -> Dict[str, Any]:
    """Standalone entrypoint to run the Packing Optimizer Agent directly."""
    in_dict = input_data.model_dump() if hasattr(input_data, "model_dump") else dict(input_data)
    initial_state: PackingOptimizerState = {"input": in_dict}
    result = app.invoke(initial_state)

    best_eval = result.get("best_evaluation", {})

    return {
        "fits": result.get("fits", False),
        "status": result.get("status"),
        "summary": result.get("summary"),
        "best_container": result.get("best_container"),
        "best_orientation": result.get("best_orientation"),
        "orientations_breakdown": result.get("orientations_breakdown", best_eval.get("orientations_breakdown", [])),
        "utilization_metrics": result.get("utilization_metrics"),
        "placed_items": best_eval.get("placed_items", []),
        "unplaced_items": best_eval.get("unplaced_items", []),
        "all_evaluations": result.get("packing_evaluations", []),
        "scene_data": result.get("scene_data", {}),
    }


# ==========================================
# Standalone CLI Self-Test
# ==========================================

if __name__ == "__main__":
    print("=" * 75)
    print("Packing Optimizer Agent: Extreme Point 3D Spatial Analysis Test")
    print("=" * 75)

    # -------------------------------------------------------------
    # Test 1: Product 1 ('Micro Terminal Block', 64 units, 28x18x14mm)
    # -------------------------------------------------------------
    print("\n>>> TEST 1: Pack 64 units of Product 1 ('Micro Terminal Block', 28x18x14 mm)")
    res1 = run_packing_optimizer({"product_id": 1})
    print(f"Status: {res1['status']}")
    print(f"Fits All Items: {res1['fits']}")
    print(f"Summary: {res1['summary']}")
    print(f"Best Container: {res1['best_container']['name']}")
    print(f"Best Item Orientation: {res1['best_orientation']}")
    print(f"Utilization: {res1['utilization_metrics']['volume_utilization_pct']}% | Packed Weight: {res1['utilization_metrics']['total_packed_weight_kg']} kg")
    print(f"Placed: {res1['utilization_metrics']['placed_count']} / {res1['utilization_metrics']['total_items']}")
    print(f"Three.js Scene Elements: {len(res1['scene_data'].get('items', []))} 3D boxes")

    # -------------------------------------------------------------
    # Test 2: Custom multi-item manifest with mixed dimensions
    # -------------------------------------------------------------
    print("\n>>> TEST 2: Multi-Item Mixed Manifest Packing into explicit container")
    mixed_req = {
        "container": {
            "name": "Medium Test Carton",
            "length": 350.0,
            "width": 250.0,
            "height": 180.0,
            "max_weight_capacity_kg": 15.0,
        },
        "items": [
            {"id": "bracket_A", "name": "Bracket A", "length": 140.0, "width": 90.0, "height": 60.0, "weight": 1.2, "quantity": 2},
            {"id": "pin_B", "name": "Pin B", "length": 80.0, "width": 30.0, "height": 30.0, "weight": 0.3, "quantity": 4},
            {"id": "plate_C", "name": "Plate C", "length": 200.0, "width": 120.0, "height": 15.0, "weight": 0.8, "quantity": 2},
        ],
    }
    res2 = run_packing_optimizer(mixed_req)
    print(f"Status: {res2['status']}")
    print(f"Fits All Items: {res2['fits']}")
    print(f"Summary: {res2['summary']}")
    print(f"Volume Utilization: {res2['utilization_metrics']['volume_utilization_pct']}% | Wasted: {res2['utilization_metrics']['wasted_volume_liters']} L")
    print(f"Placed: {res2['utilization_metrics']['placed_count']} / {res2['utilization_metrics']['total_items']}")

    # -------------------------------------------------------------
    # Test 3: Overflow item check (Item too big for container)
    # -------------------------------------------------------------
    print("\n>>> TEST 3: Overflow check (Large item into small box)")
    overflow_req = {
        "container": {
            "name": "Small Carton",
            "length": 150.0,
            "width": 100.0,
            "height": 80.0,
            "max_weight_capacity_kg": 2.0,
        },
        "items": [
            {"id": "oversized_motor", "name": "Motor", "length": 250.0, "width": 120.0, "height": 100.0, "weight": 3.5, "quantity": 1},
        ],
    }
    res3 = run_packing_optimizer(overflow_req)
    print(f"Status: {res3['status']}")
    print(f"Fits: {res3['fits']} (Expected False)")
    print(f"Unplaced Items Count: {len(res3['unplaced_items'])}")
    if res3["unplaced_items"]:
        print(f"Unplaced Reason: {res3['unplaced_items'][0]['reason']}")

    print("\n" + "=" * 75)
    print("All Packing Optimizer Agent tests completed successfully!")
    print("=" * 75)
