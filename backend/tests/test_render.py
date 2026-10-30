from app.custom_box.multi_unit import size_box_for_units
from app.models import Dimensions, Item
from app.render.viewer import render_custom_box


def test_render_returns_glb():
    item = Item(item_type="door",
                dimensions=Dimensions(length=2000, width=900, height=40),
                weight=25, quantity=3)
    result = size_box_for_units(item, 20, 5)
    glb = render_custom_box(result)
    assert glb[:4] == b"glTF"