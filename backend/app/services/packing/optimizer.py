from typing import List, Dict, Any, Optional
from app.services.packing.grid_packer import pack_items_into_container


STANDARD_CARTON_SIZES = [
    {"name": "Small Carton (S-1)", "length": 200.0, "width": 150.0, "height": 100.0, "max_weight_kg": 5.0},
    {"name": "Medium Carton (M-1)", "length": 300.0, "width": 200.0, "height": 150.0, "max_weight_kg": 10.0},
    {"name": "Large Carton (L-1)", "length": 400.0, "width": 300.0, "height": 200.0, "max_weight_kg": 20.0},
    {"name": "Extra Large Carton (XL-1)", "length": 500.0, "width": 400.0, "height": 300.0, "max_weight_kg": 30.0},
    {"name": "Heavy Industrial Box (IND-1)", "length": 600.0, "width": 500.0, "height": 400.0, "max_weight_kg": 50.0},
]


def optimize_packing(
    items: List[Dict[str, Any]],
    container_sizes: Optional[List[Dict[str, Any]]] = None,
    allow_rotation: bool = True,
    keep_upright: bool = False,
) -> Dict[str, Any]:
    """Find the best container among candidates that fits all items with highest volume utilization."""
    containers = container_sizes or STANDARD_CARTON_SIZES
    results = []

    for c in containers:
        c_len = float(c["length"])
        c_wid = float(c["width"])
        c_hei = float(c["height"])
        max_wt = float(c.get("max_weight_kg", 1000.0))

        pack_res = pack_items_into_container(
            c_len, c_wid, c_hei, items, allow_rotation=allow_rotation, keep_upright=keep_upright
        )

        all_placed = pack_res["unplaced_count"] == 0
        total_wt = pack_res["total_packed_weight_kg"]
        weight_ok = total_wt <= max_wt

        results.append({
            "container_name": c.get("name", f"{c_len}x{c_wid}x{c_hei}"),
            "all_items_fit": all_placed and weight_ok,
            "weight_exceeded": total_wt > max_wt,
            "utilization_pct": pack_res["volume_utilization_pct"],
            "packing_result": pack_res,
        })

    # Filter to containers where all items fit
    valid_candidates = [r for r in results if r["all_items_fit"]]

    if valid_candidates:
        # Sort by utilization descending (highest first)
        valid_candidates.sort(key=lambda r: r["utilization_pct"], reverse=True)
        best = valid_candidates[0]
        status = "optimal_container_found"
    else:
        # Fall back to container that placed the most items
        results.sort(key=lambda r: (r["packing_result"]["placed_count"], r["utilization_pct"]), reverse=True)
        best = results[0] if results else None
        status = "partial_fit_only"

    return {
        "status": status,
        "best_option": best,
        "all_evaluations": results,
    }

