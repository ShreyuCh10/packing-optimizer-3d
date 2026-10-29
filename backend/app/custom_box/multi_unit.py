from typing import List, Dict, Any, Tuple
import math


def find_factors(n: int) -> List[Tuple[int, int, int]]:
    """Find all (nx, ny, nz) grid dimensions such that nx * ny * nz = n."""
    factors = []
    for x in range(1, n + 1):
        if n % x == 0:
            rem = n // x
            for y in range(1, rem + 1):
                if rem % y == 0:
                    z = rem // y
                    factors.append((x, y, z))
    return factors


def calculate_multi_unit_layout(
    part_length: float,
    part_width: float,
    part_height: float,
    part_weight: float,
    quantity: int = 1,
    divider_thickness_mm: float = 3.0,
) -> Dict[str, Any]:
    """Calculate the optimal 3D grid arrangement of multiple parts for a given quantity (SNP)."""
    qty = max(1, quantity)
    if qty == 1:
        return {
            "quantity": 1,
            "grid": {"nx": 1, "ny": 1, "nz": 1},
            "content_dimensions_mm": {
                "length": part_length,
                "width": part_width,
                "height": part_height,
            },
            "total_part_weight_kg": round(part_weight, 3),
        }

    layouts = []
    factor_triplets = find_factors(qty)

    for nx, ny, nz in factor_triplets:
        # Bounding box of parts + internal dividers between parts
        tot_l = (nx * part_length) + (max(0, nx - 1) * divider_thickness_mm)
        tot_w = (ny * part_width) + (max(0, ny - 1) * divider_thickness_mm)
        tot_h = (nz * part_height) + (max(0, nz - 1) * divider_thickness_mm)

        surface_area = 2 * (tot_l * tot_w + tot_l * tot_h + tot_w * tot_h)
        volume = tot_l * tot_w * tot_h

        # Aspect ratio score: deviation from ideal 1:1:1 cubic ratio
        avg_dim = (tot_l + tot_w + tot_h) / 3.0
        aspect_variance = ((tot_l - avg_dim) ** 2 + (tot_w - avg_dim) ** 2 + (tot_h - avg_dim) ** 2) / 3.0

        layouts.append({
            "nx": nx,
            "ny": ny,
            "nz": nz,
            "length": round(tot_l, 2),
            "width": round(tot_w, 2),
            "height": round(tot_h, 2),
            "surface_area": round(surface_area, 2),
            "volume": round(volume, 2),
            "score": surface_area + math.sqrt(aspect_variance),
        })

    # Sort layouts by score (minimizing wasted surface area and extreme aspect ratios)
    layouts.sort(key=lambda item: item["score"])
    best = layouts[0]

    return {
        "quantity": qty,
        "grid": {"nx": best["nx"], "ny": best["ny"], "nz": best["nz"]},
        "content_dimensions_mm": {
            "length": best["length"],
            "width": best["width"],
            "height": best["height"],
        },
        "total_part_weight_kg": round(part_weight * qty, 3),
        "divider_thickness_mm": divider_thickness_mm,
        "alternative_layouts_count": len(layouts),
    }

