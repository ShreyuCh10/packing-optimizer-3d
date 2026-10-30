from app.models import Dimensions, Item, CustomBoxResult, Placement

def size_custom_box(item: Item, padding: float):
    """Size a custom box around one item.

    padding is the clearance on EACH side, in mm, so every dimension
    grows by 2 * padding (one gap on each side of the item).
    """

    if padding<0:
       raise ValueError("padding must be 0 or greater")

    d = item.dimensions

    box = Dimensions(
        length = d.length+2*padding,
        width = d.width+2*padding,
        height = d.height+2*padding,
    )

    item_volume =d.length*d.width*d.height
    box_volume = box.length*box.width*box.height

     # min() guards against floating-point results like 1.0000000000000002
    utilization = min(item_volume / box_volume, 1.0)

    return CustomBoxResult(
        box_dimensions=box,
        volume=box_volume,
        utilization=utilization,
        padding_used=padding,
        units_packed=1,
        placements=[
            Placement(position=(padding, padding, padding), size=d)
        ],
    )
