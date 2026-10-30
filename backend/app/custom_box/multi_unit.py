import math
from app.models import CustomBoxResult, Dimensions, Item, Placement
from app.custom_box.constraints import ConstraintError, check_constraints

MAX_UNITS_SEARCH = 100

def find_max_units(item, padding, max_stack, max_weight_kg) -> CustomBoxResult:
    limit = MAX_UNITS_SEARCH
    if item.weight is not None:
        limit = min(limit, int(max_weight_kg // item.weight))   # BEFORE: weight cap
        if limit < 1:
            raise ConstraintError(
                f"One unit ({item.weight} kg) exceeds the {max_weight_kg} kg limit."
            )

    best = None
    for n in range(1, limit + 1):
        candidate = item.model_copy(update={"quantity": n})
        result = size_box_for_units(candidate, padding, max_stack)   # geometry only
        try:
            check_constraints(candidate, result, max_weight_kg)      # AFTER: final guard
        except ConstraintError:
            break
        best = result
    if best is None:
        raise ConstraintError("Even one unit breaks the size limit.")
    return best

def size_box_for_units(item: Item, padding: float, max_stack: int) -> CustomBoxResult:
    """Size one box for item.quantity identical items.

    Items are arranged in a grid of nx * ny * nz (along length, width, height).
    Padding goes around the whole block once, not around each item.
    Assumptions: items touch each other, orientation is fixed.
    The grid with the smallest box volume wins; nz is limited by max_stack.
    """

    if padding<0:
        raise ValueError("padding must be 0 or greater")
    if max_stack<1:
        raise ValueError("max_stack must be at least 1")

    d = item.dimensions
    n = item.quantity

    # 1. Search every grid shape and remember the smallest box
    best = None
    for nz in range(1, min(max_stack, n)+1):
        for ny in range(1,n+1):
            nx = math.ceil(n/(ny*nz))
            length = nx*d.length+2*padding
            width = ny*d.width+2*padding
            height=nz*d.height+2*padding
            volume=length*width*height
            if best is None or volume<best[0]:
                best=(volume,nx,ny,nz)

    box_volume, nx,ny, nz = best
    box = Dimensions(
        length=nx * d.length + 2 * padding,
        width=ny * d.width + 2 * padding,
        height=nz * d.height + 2 * padding,
    )

    # 2. Place items layer by layer until all n are placed
    placements = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if len(placements)==n:
                    break
                placements.append(
                    Placement(
                         position=(
                            padding + i * d.length,
                            padding + j * d.width,
                            padding + k * d.height,
                        ),
                        size=d,
                    )
                )

    item_volume = d.length * d.width * d.height
    utilization = min(n * item_volume / box_volume, 1.0)

    return CustomBoxResult(
        box_dimensions=box,
        volume=box_volume,
        utilization=utilization,
        padding_used=padding,
        units_packed=n,
        placements=placements,
    )    