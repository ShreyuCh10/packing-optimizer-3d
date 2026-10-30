import pytest

from app.custom_box.multi_unit import size_box_for_units
from app.models import Dimensions, Item


def make_doors(n):
    return Item(
        item_type="door",
        dimensions=Dimensions(length=2000, width=900, height=40),
        weight=25,
        quantity=n,
    )


def overlaps(a, b):
    sa = (a.size.length, a.size.width, a.size.height)
    sb = (b.size.length, b.size.width, b.size.height)
    for i in range(3):
        if a.position[i] + sa[i] <= b.position[i] or b.position[i] + sb[i] <= a.position[i]:
            return False
    return True


def test_one_unit_matches_single_item_box():
    r = size_box_for_units(make_doors(1), padding=20, max_stack=5)
    assert (r.box_dimensions.length, r.box_dimensions.width, r.box_dimensions.height) == (2040, 940, 80)


def test_five_doors_stack_flat():
    # hand calculation: 5 * 40 + 2 * 20 = 240
    r = size_box_for_units(make_doors(5), padding=20, max_stack=5)
    assert (r.box_dimensions.length, r.box_dimensions.width, r.box_dimensions.height) == (2040, 940, 240)
    assert r.volume == pytest.approx(460_224_000)


def test_stack_limit_respected():
    r = size_box_for_units(make_doors(8), padding=20, max_stack=5)
    layers = round((r.box_dimensions.height - 40) / 40)
    assert layers <= 5


def test_placement_count_equals_quantity():
    for n in (1, 3, 7, 12):
        r = size_box_for_units(make_doors(n), padding=20, max_stack=5)
        assert len(r.placements) == n
        assert r.units_packed == n


def test_no_overlap_and_all_inside_box():
    r = size_box_for_units(make_doors(8), padding=20, max_stack=5)
    b = r.box_dimensions
    for p in r.placements:
        assert p.position[0] + p.size.length <= b.length
        assert p.position[1] + p.size.width <= b.width
        assert p.position[2] + p.size.height <= b.height
        assert min(p.position) >= 0
    for i in range(len(r.placements)):
        for j in range(i + 1, len(r.placements)):
            assert not overlaps(r.placements[i], r.placements[j])


def test_utilization_between_0_and_1():
    r = size_box_for_units(make_doors(5), padding=20, max_stack=5)
    assert 0 < r.utilization <= 1


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        size_box_for_units(make_doors(2), padding=-1, max_stack=5)
    with pytest.raises(ValueError):
        size_box_for_units(make_doors(2), padding=20, max_stack=0)