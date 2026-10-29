from typing import List, Dict, Any


# Distinct visual color palette for items in 3D viewer
COLOR_PALETTE = [
    "#3B82F6",  # Blue
    "#10B981",  # Green
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#F97316",  # Orange
]


def generate_scene_data(packing_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format packing result into 3D scene description for Three.js frontend renderer."""
    container = packing_result.get("container_dimensions", {})
    placed_items = packing_result.get("placed_items", [])

    scene_items = []
    for idx, item in enumerate(placed_items):
        pos = item.get("position", {})
        dims = item.get("dimensions", {})
        color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]

        scene_items.append({
            "id": item.get("item_id", f"item_{idx}"),
            "color": color,
            "position": {
                "x": pos.get("x", 0.0) + (dims.get("length", 0.0) / 2.0),
                "y": pos.get("y", 0.0) + (dims.get("width", 0.0) / 2.0),
                "z": pos.get("z", 0.0) + (dims.get("height", 0.0) / 2.0),
            },
            "dimensions": dims,
            "weight_kg": item.get("weight_kg", 0.0),
        })

    return {
        "container": {
            "dimensions": container,
            "center": {
                "x": container.get("length", 0.0) / 2.0,
                "y": container.get("width", 0.0) / 2.0,
                "z": container.get("height", 0.0) / 2.0,
            },
        },
        "items": scene_items,
        "metrics": {
            "volume_utilization_pct": packing_result.get("volume_utilization_pct", 0.0),
            "placed_count": len(placed_items),
        },
    }

