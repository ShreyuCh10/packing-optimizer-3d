from typing import List, Dict, Any, Optional
from app.services.packing.orientations import get_possible_orientations


class PlacedItem:
    def __init__(self, item_id: str, x: float, y: float, z: float, dx: float, dy: float, dz: float, weight: float = 0.0):
        self.item_id = item_id
        self.x = x
        self.y = y
        self.z = z
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.weight = weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "position": {"x": round(self.x, 2), "y": round(self.y, 2), "z": round(self.z, 2)},
            "dimensions": {"length": round(self.dx, 2), "width": round(self.dy, 2), "height": round(self.dz, 2)},
            "weight_kg": round(self.weight, 3),
        }

    def overlaps(self, other: "PlacedItem") -> bool:
        """Check if 3D bounding boxes intersect."""
        return not (
            self.x + self.dx <= other.x or
            other.x + other.dx <= self.x or
            self.y + self.dy <= other.y or
            other.y + other.dy <= self.y or
            self.z + self.dz <= other.z or
            other.z + other.dz <= self.z
        )


def pack_items_into_container(
    container_length: float,
    container_width: float,
    container_height: float,
    items: List[Dict[str, Any]],
    allow_rotation: bool = True,
    keep_upright: bool = False,
) -> Dict[str, Any]:
    """Fit items into a container using a 3D Guillotine / Corner-point packing heuristic."""
    placed: List[PlacedItem] = []
    unplaced: List[Dict[str, Any]] = []

    # Sort items by volume descending (largest first)
    sorted_items = sorted(
        items,
        key=lambda it: it.get("length", 0) * it.get("width", 0) * it.get("height", 0),
        reverse=True,
    )

    # Candidate placement coordinate points, starting at origin (0, 0, 0)
    candidate_points = [(0.0, 0.0, 0.0)]

    for idx, item in enumerate(sorted_items):
        item_id = item.get("id", f"item_{idx + 1}")
        l = float(item.get("length", 0))
        w = float(item.get("width", 0))
        h = float(item.get("height", 0))
        weight = float(item.get("weight", 0.0))

        orientations = get_possible_orientations(
            l, w, h,
            allow_rotation=item.get("allow_rotation", allow_rotation),
            keep_upright=item.get("keep_upright", keep_upright),
        )

        item_placed = False

        # Sort candidate points by z, then y, then x (bottom-to-top, back-to-front, left-to-right)
        candidate_points.sort(key=lambda pt: (pt[2], pt[1], pt[0]))

        for pt in candidate_points:
            px, py, pz = pt

            for dx, dy, dz in orientations:
                # Check container boundaries
                if px + dx > container_length or py + dy > container_width or pz + dz > container_height:
                    continue

                candidate = PlacedItem(item_id, px, py, pz, dx, dy, dz, weight)

                # Check overlap with already placed items
                collision = any(candidate.overlaps(other) for other in placed)
                if not collision:
                    placed.append(candidate)
                    item_placed = True

                    # Generate new candidate corner points
                    candidate_points.append((px + dx, py, pz))
                    candidate_points.append((px, py + dy, pz))
                    candidate_points.append((px, py, pz + dz))
                    break

            if item_placed:
                break

        if not item_placed:
            unplaced.append({
                "item_id": item_id,
                "dimensions": {"length": l, "width": w, "height": h},
                "weight_kg": weight,
                "reason": "Does not fit within container boundaries or clashes with placed items",
            })

    container_volume = container_length * container_width * container_height
    total_placed_volume = sum(item.dx * item.dy * item.dz for item in placed)
    total_placed_weight = sum(item.weight for item in placed)
    utilization_pct = (total_placed_volume / max(1.0, container_volume)) * 100.0

    return {
        "container_dimensions": {
            "length": container_length,
            "width": container_width,
            "height": container_height,
            "volume_liters": round(container_volume / 1000000.0, 3),
        },
        "placed_count": len(placed),
        "unplaced_count": len(unplaced),
        "total_items": len(items),
        "volume_utilization_pct": round(min(100.0, utilization_pct), 2),
        "total_packed_weight_kg": round(total_placed_weight, 3),
        "placed_items": [item.to_dict() for item in placed],
        "unplaced_items": unplaced,
    }

