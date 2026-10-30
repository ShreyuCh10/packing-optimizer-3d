import pytest

from app.custom_box.constraints import ConstraintError, check_constraints
from app.custom_box.multi_unit import size_box_for_units
from app.models import Dimensions, Item


def make(n, weight=25):
    return Item(item_type="door",
                dimensions=Dimensions(length=2000, width=900, height=40),
                weight=weight, quantity=n)


def test_normal_box_passes():
    item = make(2)
    check_constraints(item, size_box_for_units(item, 20, 5))


def test_too_heavy_rejected():
    item = make(2, weight=100)  # 200 kg total
    with pytest.raises(ConstraintError):
        check_constraints(item, size_box_for_units(item, 20, 5))