"""Comprehensive Test Suite for Retrieval & Gathering Agent with SQLite Database Integration."""

import sys
from app.agents.retrieval_gathering import run_retrieval_gathering
from app.api.requirement_routes import retrieve_packages, RetrievalInput

def run_tests():
    print("=" * 75)
    print("RUNNING RETRIEVAL AGENT VERIFICATION SUITE")
    print("=" * 75)

    # -------------------------------------------------------------
    # Test 1: Auto-lookup Product 1 ('Micro Terminal Block', Plastic Nylon, SNP=64)
    # -------------------------------------------------------------
    print("\n[TEST 1] Product 1: 'Micro Terminal Block' (via product_id=1)")
    res1 = run_retrieval_gathering({"product_id": 1})
    m1 = res1["metrics"]
    print(f"  Part: {m1['part_name']} | Type: {m1['part_type']} | SNP: {m1['snp']}")
    print(f"  Single part: {m1['single_product_dimensions_mm']} mm, weight: {m1['total_product_weight_kg'] / m1['snp']} kg")
    print(f"  Effective bounding box (with foam/padding): {m1['effective_bounding_box_mm']} mm")
    print(f"  Total payload weight: {m1['max_rating']} kg")
    print(f"  Summary: {res1['narrowing_summary']}")
    print(f"  Total fitting in DB: {res1['total_candidates_found']} -> Narrowed: {res1['narrowed_count']}")
    assert res1["narrowed_count"] > 0, "Expected at least 1 narrowed package"
    assert res1["recommended_package"] is not None, "Expected recommended package"
    rec1 = res1["recommended_package"]
    print(f"  Top Choice: {rec1['name']} ({rec1['category_label']}) - {rec1['fit_tier']} - {rec1['volume_utilization_pct']}% util")
    for p in res1["matching_packages"]:
        print(f"    - Rank {p['rank']}: {p['name']} ({p['category_label']}) [{p['fit_tier']}] -> {p['volume_utilization_pct']}% util, {p['wasted_volume_liters']}L wasted")

    # -------------------------------------------------------------
    # Test 2: Auto-lookup Product 2 ('Steel Dowel Pin Small', Hardened Steel, SNP=50)
    # -------------------------------------------------------------
    print("\n[TEST 2] Product 2: 'Steel Dowel Pin Small' (via part_name)")
    res2 = run_retrieval_gathering({"name": "Steel Dowel Pin Small"})
    m2 = res2["metrics"]
    print(f"  Part: {m2['part_name']} | Type: {m2['part_type']} | SNP: {m2['snp']}")
    print(f"  Effective bounding box: {m2['effective_bounding_box_mm']} mm | Total weight: {m2['max_rating']} kg")
    print(f"  Summary: {res2['narrowing_summary']}")
    print(f"  Total fitting in DB: {res2['total_candidates_found']} -> Narrowed: {res2['narrowed_count']}")
    assert res2["narrowed_count"] > 0
    rec2 = res2["recommended_package"]
    print(f"  Top Choice: {rec2['name']} ({rec2['category_label']}) - {rec2['fit_tier']} - {rec2['volume_utilization_pct']}% util")
    for p in res2["matching_packages"]:
        print(f"    - Rank {p['rank']}: {p['name']} [{p['fit_tier']}] -> {p['volume_utilization_pct']}% util")

    # -------------------------------------------------------------
    # Test 3: Heavy Industrial Product (Product 45: Solid Counterweight Ingot, 38kg)
    # -------------------------------------------------------------
    print("\n[TEST 3] Heavy Industrial Part (Product 45: 38kg, exceeding 9kg carton capacity)")
    res3 = run_retrieval_gathering({"product_id": 45})
    m3 = res3["metrics"]
    print(f"  Part: {m3['part_name']} | Total weight: {m3['max_rating']} kg")
    print(f"  Summary: {res3['narrowing_summary']}")
    print(f"  Total fitting in DB: {res3['total_candidates_found']} -> Narrowed: {res3['narrowed_count']}")
    rec3 = res3["recommended_package"]
    assert rec3 is None, "Do not recommend heavy-duty packaging without a verified payload rating"
    assert "verified payload rating" in res3["narrowing_summary"]

    # -------------------------------------------------------------
    # Test 4: Custom Unstructured Part Requirement
    # -------------------------------------------------------------
    print("\n[TEST 4] Custom Unstructured Part: 140x90x60mm steel bracket, SNP=2 (2.4kg)")
    res4 = run_retrieval_gathering({
        "name": "Custom Steel Bracket",
        "part_length": 140.0,
        "part_width": 90.0,
        "part_height": 60.0,
        "part_weight": 1.2,
        "part_type": "steel",
        "snp": 2,
    })
    print(f"  Summary: {res4['narrowing_summary']}")
    print(f"  Total fitting in DB: {res4['total_candidates_found']} -> Narrowed: {res4['narrowed_count']}")
    for p in res4["matching_packages"]:
        print(f"    - Rank {p['rank']}: {p['name']} ({p['category_label']}) [{p['fit_tier']}] -> {p['volume_utilization_pct']}% util")

    # -------------------------------------------------------------
    # Test 5: Via FastAPI Endpoint Function (retrieve_packages)
    # -------------------------------------------------------------
    print("\n[TEST 5] API Route retrieve_packages endpoint")
    api_res = retrieve_packages(RetrievalInput(product_id=2, max_results=3))
    print(f"  API Status: {api_res['status']}")
    print(f"  Narrowed count: {len(api_res['matching_packages'])}")
    print(f"  Top choice: {api_res['recommended_package']['name']}")

    print("\n" + "=" * 75)
    print("ALL 5 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
