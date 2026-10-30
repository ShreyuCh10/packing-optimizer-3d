MAX_BOX_DIMENSION_MM = 2500
MAX_MANUAL_CARRY_KG = 25       # one person (placeholder, confirm)
MAX_MECHANICAL_KG = 150        # forklift / trolley (placeholder, confirm)


class ConstraintError(ValueError):
    """The designed box breaks a manufacturing or shipping limit."""


def check_constraints(item, result, max_weight_kg: float) -> None:
    b = result.box_dimensions
    for name, value in (("length", b.length), ("width", b.width), ("height", b.height)):
        if value > MAX_BOX_DIMENSION_MM:
            raise ConstraintError(
                f"Box {name} {value:.0f} mm exceeds the maximum of {MAX_BOX_DIMENSION_MM} mm."
            )
    if item.weight is not None:
        total = item.weight * result.units_packed
        if total > max_weight_kg:
            raise ConstraintError(
                f"Total weight {total:.1f} kg exceeds the maximum of {max_weight_kg} kg."
            )