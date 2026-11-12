
import math

from app.models import CustomBoxResult, Dimensions, Item, Placement
from app.custom_box.constraints import ConstraintError


def calculate_packaging_weight(
    box_dimensions: Dimensions,
    wall_thickness_mm: float,
    density_kg_m3: float,
) -> float:
    """Estimate six-wall box weight using material density."""

    outer_volume = (
        box_dimensions.length
        * box_dimensions.width
        * box_dimensions.height
    )

    inner_length = box_dimensions.length - 2 * wall_thickness_mm
    inner_width = box_dimensions.width - 2 * wall_thickness_mm
    inner_height = box_dimensions.height - 2 * wall_thickness_mm

    if min(inner_length, inner_width, inner_height) <= 0:
        raise ConstraintError("Wall thickness is too large for this box.")

    inner_volume = inner_length * inner_width * inner_height
    wall_volume_m3 = (outer_volume - inner_volume) / 1_000_000_000

    return wall_volume_m3 * density_kg_m3


def _find_best_arrangement(
    item: Item,
    quantity: int,
    padding: float,
    max_stack: int,
    wall_thickness_mm: float,
    max_box_dimensions: Dimensions | None = None,
):
    """Find the smallest feasible grid without creating placements."""

    dimensions = item.dimensions
    clearance = padding + wall_thickness_mm

    if max_box_dimensions is not None:
        usable_length = max_box_dimensions.length - 2 * clearance
        usable_width = max_box_dimensions.width - 2 * clearance
        usable_height = max_box_dimensions.height - 2 * clearance

        if min(usable_length, usable_width, usable_height) <= 0:
            return None

        max_x = math.floor(usable_length / dimensions.length)
        max_y = math.floor(usable_width / dimensions.width)
        max_z = min(
            max_stack,
            math.floor(usable_height / dimensions.height),
            quantity,
        )
    else:
        max_x = quantity
        max_y = quantity
        max_z = min(max_stack, quantity)

    if min(max_x, max_y, max_z) < 1:
        return None

    best = None

    for nz in range(1, max_z + 1):
        for ny in range(1, min(quantity, max_y) + 1):
            nx = math.ceil(quantity / (ny * nz))

            if nx > max_x:
                continue

            outer_length = (
                nx * dimensions.length + 2 * clearance
            )
            outer_width = (
                ny * dimensions.width + 2 * clearance
            )
            outer_height = (
                nz * dimensions.height + 2 * clearance
            )

            volume = outer_length * outer_width * outer_height

            if best is None or volume < best[0]:
                best = (
                    volume,
                    nx,
                    ny,
                    nz,
                    Dimensions(
                        length=outer_length,
                        width=outer_width,
                        height=outer_height,
                    ),
                )

    return best


def find_max_units(
    item: Item,
    padding: float,
    max_stack: int,
    max_weight_kg: float,
    max_box_dimensions: Dimensions,
    wall_thickness_mm: float,
    density_kg_m3: float,
) -> CustomBoxResult:
    """Find the maximum quantity satisfying all configured constraints."""

    dimensions = item.dimensions
    clearance = padding + wall_thickness_mm

    usable_length = max_box_dimensions.length - 2 * clearance
    usable_width = max_box_dimensions.width - 2 * clearance
    usable_height = max_box_dimensions.height - 2 * clearance

    if min(usable_length, usable_width, usable_height) <= 0:
        raise ConstraintError(
            "The configured box dimensions are too small for the "
            "selected padding and wall thickness."
        )

    max_x = math.floor(usable_length / dimensions.length)
    max_y = math.floor(usable_width / dimensions.width)
    max_z = min(
        max_stack,
        math.floor(usable_height / dimensions.height),
    )

    max_possible_units = max_x * max_y * max_z

    if max_possible_units < 1:
        raise ConstraintError(
            "Even one unit cannot fit within the configured box dimensions."
        )

    # Product weight alone gives an upper bound.
    if item.weight > 0:
        max_possible_units = min(
            max_possible_units,
            math.floor(max_weight_kg / item.weight),
        )

    if max_possible_units < 1:
        raise ConstraintError(
            "Even one unit exceeds the configured lifting limit."
        )

    # Search downward and stop at the first feasible quantity.
    for quantity in range(max_possible_units, 0, -1):
        arrangement = _find_best_arrangement(
            item=item,
            quantity=quantity,
            padding=padding,
            max_stack=max_stack,
            wall_thickness_mm=wall_thickness_mm,
            max_box_dimensions=max_box_dimensions,
        )

        if arrangement is None:
            continue

        _, _, _, _, box_dimensions = arrangement

        packaging_weight = calculate_packaging_weight(
            box_dimensions,
            wall_thickness_mm,
            density_kg_m3,
        )

        total_weight = (
            item.weight * quantity + packaging_weight
        )

        if total_weight > max_weight_kg:
            continue

        # Generate placement objects only for the final result.
        return size_box_for_units(
            item.model_copy(update={"quantity": quantity}),
            padding,
            max_stack,
            wall_thickness_mm,
            max_box_dimensions,
        )

    raise ConstraintError(
        "Even one unit exceeds the configured box or lifting limits."
    )


def size_box_for_units(
    item: Item,
    padding: float,
    max_stack: int,
    wall_thickness_mm: float,
    max_box_dimensions: Dimensions | None = None,
) -> CustomBoxResult:
    """Calculate the smallest feasible outer box and product placements."""

    if padding < 0:
        raise ValueError("Padding must be zero or greater.")

    if max_stack < 1:
        raise ValueError("Maximum stack must be at least 1.")

    if wall_thickness_mm <= 0:
        raise ValueError("Wall thickness must be greater than zero.")

    if item.quantity is None:
        raise ValueError("Item quantity is required.")

    quantity = item.quantity
    dimensions = item.dimensions

    best = _find_best_arrangement(
        item=item,
        quantity=quantity,
        padding=padding,
        max_stack=max_stack,
        wall_thickness_mm=wall_thickness_mm,
        max_box_dimensions=max_box_dimensions,
    )

    if best is None:
        raise ConstraintError(
            f"{quantity} units cannot fit within the configured "
            "box dimensions."
        )

    box_volume, nx, ny, nz, box = best

    placements = []

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if len(placements) >= quantity:
                    break

                placements.append(
                    Placement(
                        position=(
                            wall_thickness_mm + padding
                            + i * dimensions.length,
                            wall_thickness_mm + padding
                            + j * dimensions.width,
                            wall_thickness_mm + padding
                            + k * dimensions.height,
                        ),
                        size=dimensions,
                    )
                )

            if len(placements) >= quantity:
                break

        if len(placements) >= quantity:
            break

    product_volume = (
        dimensions.length
        * dimensions.width
        * dimensions.height
    )

    utilization = min(
        quantity * product_volume / box_volume,
        1.0,
    )

    return CustomBoxResult(
        box_dimensions=box,
        volume=box_volume,
        utilization=utilization,
        padding_used=padding,
        units_packed=quantity,
        placements=placements,
    )
