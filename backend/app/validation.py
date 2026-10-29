from typing import Dict, Any, List


def validate_part_dimensions(length: float, width: float, height: float, weight: float) -> List[str]:
    """Validate standard physical limits for part dimensions."""
    errors = []
    if length <= 0 or width <= 0 or height <= 0:
        errors.append("Dimensions (length, width, height) must all be greater than zero.")
    if weight < 0:
        errors.append("Weight cannot be negative.")
    if length > 5000 or width > 5000 or height > 5000:
        errors.append("Individual dimension exceeds maximum supported size (5000 mm).")
    return errors

