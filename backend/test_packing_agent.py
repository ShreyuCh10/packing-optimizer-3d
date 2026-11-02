"""Comprehensive Verification Suite for Packing Optimizer Agent (Extreme Point 3D Analysis)."""

from app.agents.packing_optimizer import run_packing_optimizer
from app.api.packing_routes import run_packing_agent_endpoint

def run_tests():
    print("=" * 75)
    print("RUNNING PACKING OPTIMIZER AGENT VERIFICATION SUITE")
    print("=" * 75)

    # -------------------------------------------------------------
    # Test 1: Pack 64 units of Product 1 ('Micro Terminal Block', 28x18x14mm)
    # -------------------------------------------------------------
    print("\n[TEST 1] Product 1: 'Micro Terminal Block' (64 units auto-packed into DB Package 1)")
    res1 = run_packing_optimizer({"product_id": 1})
    print(f"  Status: {res1['status']}")
    print(f"  Fits: {res1['fits']}")
    print(f"  Best Container: {res1['best_container']['name']}")
    print(f"  Best Orientation: {res1['best_orientation']}")
    print(f"  Placed Items: {res1['utilization_metrics']['placed_count']} / {res1['utilization_metrics']['total_items']}")
    print(f"  Volume Utilization: {res1['utilization_metrics']['volume_utilization_pct']}%")
    print(f"  Packed Weight: {res1['utilization_metrics']['total_packed_weight_kg']} kg")
    assert res1["fits"] is True, "Expected all 64 items to fit"
    assert res1["utilization_metrics"]["placed_count"] == 64, "All 64 items should be placed"
    assert len(res1["scene_data"]["items"]) == 64, "Scene data should contain 64 items"

    # -------------------------------------------------------------
    # Test 2: Pack Product 2 ('Steel Dowel Pin Small', 50 units, 35x10x10mm)
    # -------------------------------------------------------------
    print("\n[TEST 2] Product 2: 'Steel Dowel Pin Small' (50 units auto-packed)")
    res2 = run_packing_optimizer({"product_id": 2})
    print(f"  Status: {res2['status']}")
    print(f"  Fits: {res2['fits']}")
    print(f"  Best Container: {res2['best_container']['name']}")
    print(f"  Best Orientation: {res2['best_orientation']}")
    print(f"  Placed: {res2['utilization_metrics']['placed_count']} / {res2['utilization_metrics']['total_items']}")
    assert res2["fits"] is True
    assert res2["utilization_metrics"]["placed_count"] == 50

    # -------------------------------------------------------------
    # Test 3: Mixed multi-item packing into explicit container
    # -------------------------------------------------------------
    print("\n[TEST 3] Mixed Multi-Item Packing (Brackets + Pins + Plates)")
    res3 = run_packing_optimizer({
        "container": {
            "name": "Custom Shipping Box",
            "length": 350.0,
            "width": 250.0,
            "height": 180.0,
            "max_weight_capacity_kg": 20.0,
        },
        "items": [
            {"id": "bracket", "name": "Bracket", "length": 140.0, "width": 90.0, "height": 60.0, "weight": 1.5, "quantity": 2},
            {"id": "pin", "name": "Pin", "length": 70.0, "width": 30.0, "height": 30.0, "weight": 0.4, "quantity": 4},
            {"id": "plate", "name": "Plate", "length": 220.0, "width": 100.0, "height": 20.0, "weight": 0.9, "quantity": 2},
        ],
    })
    print(f"  Status: {res3['status']}")
    print(f"  Fits: {res3['fits']}")
    print(f"  Volume Utilization: {res3['utilization_metrics']['volume_utilization_pct']}%")
    print(f"  Wasted Volume: {res3['utilization_metrics']['wasted_volume_liters']} L")
    print(f"  Placed: {res3['utilization_metrics']['placed_count']} / {res3['utilization_metrics']['total_items']}")
    assert res3["fits"] is True
    assert res3["utilization_metrics"]["placed_count"] == 8

    # -------------------------------------------------------------
    # Test 4: Container Overflow Detection
    # -------------------------------------------------------------
    print("\n[TEST 4] Overflow Detection: Large Item vs Small Container")
    res4 = run_packing_optimizer({
        "container": {
            "name": "Tiny Carton",
            "length": 100.0,
            "width": 80.0,
            "height": 50.0,
            "max_weight_capacity_kg": 2.0,
        },
        "items": [
            {"id": "large_part", "name": "Large Part", "length": 200.0, "width": 150.0, "height": 100.0, "weight": 3.0, "quantity": 1},
        ],
    })
    print(f"  Status: {res4['status']}")
    print(f"  Fits: {res4['fits']} (Expected False)")
    print(f"  Unplaced count: {len(res4['unplaced_items'])}")
    print(f"  Unplaced reason: {res4['unplaced_items'][0]['reason']}")
    assert res4["fits"] is False
    assert len(res4["unplaced_items"]) == 1

    # -------------------------------------------------------------
    # Test 5: API Route run_packing_agent_endpoint
    # -------------------------------------------------------------
    print("\n[TEST 5] FastAPI Endpoint run_packing_agent_endpoint")
    api_res = run_packing_agent_endpoint({"product_id": 1})
    print(f"  API Status: {api_res['status']}")
    print(f"  Fits: {api_res['fits']}")
    print(f"  Container: {api_res['best_container']['name']}")
    assert api_res["fits"] is True

    print("\n" + "=" * 75)
    print("ALL 5 PACKING OPTIMIZER AGENT TESTS PASSED (100% SUCCESS)!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()

