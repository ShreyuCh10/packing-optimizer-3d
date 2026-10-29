from typing import Dict, Any, List


def validate_box_constraints(
    external_length_mm: float,
    external_width_mm: float,
    external_height_mm: float,
    gross_weight_kg: float,
    material_max_weight_kg: float = 35.0,
    carrier_max_weight_kg: float = 70.0,
    carrier_max_length_mm: float = 2740.0,
    carrier_max_girth_mm: float = 4000.0,
) -> Dict[str, Any]:
    """Validate box physical constraints against material strength and carrier shipping limits."""
    violations: List[str] = []
    warnings: List[str] = []

    # Sort dimensions to find longest side
    dims = sorted([external_length_mm, external_width_mm, external_height_mm], reverse=True)
    length, dim2, dim3 = dims[0], dims[1], dims[2]

    # Girth calculation: Length + 2*(W + H)
    length_plus_girth = length + 2 * (dim2 + dim3)

    if gross_weight_kg > material_max_weight_kg:
        violations.append(
            f"Gross weight ({gross_weight_kg:.1f} kg) exceeds box material maximum capacity ({material_max_weight_kg:.1f} kg)."
        )

    if gross_weight_kg > carrier_max_weight_kg:
        violations.append(
            f"Gross weight ({gross_weight_kg:.1f} kg) exceeds standard parcel carrier limit ({carrier_max_weight_kg:.1f} kg). Requires freight shipping."
        )

    if length > carrier_max_length_mm:
        violations.append(
            f"Longest dimension ({length:.1f} mm) exceeds carrier maximum parcel length ({carrier_max_length_mm:.1f} mm)."
        )

    if length_plus_girth > carrier_max_girth_mm:
        violations.append(
            f"Length + Girth ({length_plus_girth:.1f} mm) exceeds carrier maximum ({carrier_max_girth_mm:.1f} mm)."
        )

    # Aspect ratio check
    if dim3 > 0 and (length / dim3) > 5.0:
        warnings.append(
            f"High aspect ratio ({length / dim3:.1f}:1). Box may be prone to bending or crush damage during transit."
        )

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "metrics": {
            "longest_edge_mm": length,
            "length_plus_girth_mm": round(length_plus_girth, 1),
            "gross_weight_kg": round(gross_weight_kg, 2),
            "material_capacity_utilization_pct": round((gross_weight_kg / max(1.0, material_max_weight_kg)) * 100, 1),
        },
    }

