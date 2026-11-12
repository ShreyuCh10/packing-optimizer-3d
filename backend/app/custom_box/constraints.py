
from app.models import Dimensions


class ConstraintError(ValueError):
    """The designed box breaks a manufacturing or handling limit."""


def check_constraints(
    item,
    result,
    max_weight_kg: float,
    max_box_dimensions: Dimensions,
    packaging_weight_kg: float = 0.0,
) -> None:
    box = result.box_dimensions

    dimension_limits = {
        "length": max_box_dimensions.length,
        "width": max_box_dimensions.width,
        "height": max_box_dimensions.height,
    }

    for name, actual in (
        ("length", box.length),
        ("width", box.width),
        ("height", box.height),
    ):
        maximum = dimension_limits[name]

        if actual > maximum:
            raise ConstraintError(
                f"Box {name} {actual:.1f} mm exceeds "
                f"your maximum of {maximum:.1f} mm."
            )

    product_weight = item.weight * result.units_packed
    total_weight = product_weight + packaging_weight_kg

    if total_weight > max_weight_kg:
        raise ConstraintError(
            f"Total weight including packaging "
            f"({total_weight:.2f} kg) exceeds your "
            f"lifting limit of {max_weight_kg:.2f} kg."
        )
