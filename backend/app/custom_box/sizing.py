from typing import Dict, Any


def calculate_box_dimensions(
    content_length: float,
    content_width: float,
    content_height: float,
    padding_thickness: float,
    wall_thickness: float,
    content_weight: float = 0.0,
    material_density_kg_m3: float = 140.0,
    cost_per_sqm: float = 1.50,
) -> Dict[str, Any]:
    """Calculate internal, external dimensions, volumes, and weights of a custom box."""
    # Internal dimensions (accounting for padding on opposite sides)
    internal_length = round(content_length + (2 * padding_thickness), 2)
    internal_width = round(content_width + (2 * padding_thickness), 2)
    internal_height = round(content_height + (2 * padding_thickness), 2)

    # External dimensions (accounting for container wall thickness)
    external_length = round(internal_length + (2 * wall_thickness), 2)
    external_width = round(internal_width + (2 * wall_thickness), 2)
    external_height = round(internal_height + (2 * wall_thickness), 2)

    # Volumes (converted to liters and cubic meters)
    content_volume_cm3 = (content_length * content_width * content_height) / 1000.0
    internal_volume_cm3 = (internal_length * internal_width * internal_height) / 1000.0
    external_volume_cm3 = (external_length * external_width * external_height) / 1000.0

    # Surface area in square meters (standard 6-faced box: 2*(LW + LH + WH))
    l_m = external_length / 1000.0
    w_m = external_width / 1000.0
    h_m = external_height / 1000.0
    surface_area_sqm = round(2.0 * (l_m * w_m + l_m * h_m + w_m * h_m), 4)

    # Material tare weight estimate
    wall_thickness_m = wall_thickness / 1000.0
    box_tare_weight_kg = round(surface_area_sqm * wall_thickness_m * material_density_kg_m3, 3)

    # Padding volume and estimate weight (assumed ~30 kg/m3 for expanded polyethylene foam)
    padding_volume_m3 = (internal_volume_cm3 - content_volume_cm3) / 1000000.0
    padding_weight_kg = round(max(0.0, padding_volume_m3 * 30.0), 3)

    total_gross_weight_kg = round(content_weight + box_tare_weight_kg + padding_weight_kg, 3)
    estimated_cost = round(surface_area_sqm * cost_per_sqm, 2)

    # Volumetric weight (IATA standard divisor 5000: L*W*H in cm / 5000)
    volumetric_weight_kg = round((external_length / 10.0) * (external_width / 10.0) * (external_height / 10.0) / 5000.0, 2)

    return {
        "internal_dimensions_mm": {
            "length": internal_length,
            "width": internal_width,
            "height": internal_height,
        },
        "external_dimensions_mm": {
            "length": external_length,
            "width": external_width,
            "height": external_height,
        },
        "volumes_liters": {
            "content": round(content_volume_cm3 / 1000.0, 3),
            "internal": round(internal_volume_cm3 / 1000.0, 3),
            "external": round(external_volume_cm3 / 1000.0, 3),
        },
        "surface_area_sqm": surface_area_sqm,
        "weights_kg": {
            "content": round(content_weight, 3),
            "tare_box": box_tare_weight_kg,
            "padding": padding_weight_kg,
            "gross": total_gross_weight_kg,
            "volumetric": volumetric_weight_kg,
        },
        "estimated_material_cost": estimated_cost,
    }

