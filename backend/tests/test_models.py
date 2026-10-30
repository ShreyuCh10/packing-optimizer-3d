import pytest
from pydantic import ValidationError
from app.models import Dimensions, Item


def test_valid_dimensions():
    d = Dimensions(length=100, width=50, height=20)
    assert d.length == 100

def test_negative_length_rejected():
    with pytest.raises(ValidationError):
        Dimensions(length=-5, width=50, height=20)

def test_valid_item():
    item = Item(dimensions=Dimensions(length=2000, width=900, height=40),
                weight=25, quantity=3)
    assert item.quantity == 3

def test_zero_quantity_rejected():
    with pytest.raises(ValidationError):
        Item(dimensions=Dimensions(length=2000, width=900, height=40),
             weight=25, quantity=0)

def test_negative_weight_rejected():
     with pytest.raises(ValidationError):
         Item(dimensions=Dimensions(length=2000, width=900, height=40),
                      weight=-5, quantity=3)

