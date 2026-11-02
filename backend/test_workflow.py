"""End-to-End Verification Suite for Unified 3-Agent Workflow (Requirement -> Retrieval -> Packing Optimizer)."""

from app.agents.workflow import run_unified_workflow
from app.api.requirement_routes import run_workflow_endpoint

def run_tests():
    print("=" * 80)
    print("RUNNING UNIFIED 3-AGENT PACKAGING WORKFLOW TEST SUITE")
    print("=" * 80)

    # -------------------------------------------------------------
    # Scenario 1: Natural Language Text Requirement
    # -------------------------------------------------------------
    print("\n[SCENARIO 1] Free-form text requirement string")
    prompt = "I need packaging for 4 steel brackets measuring length 140mm, width 90mm, height 60mm and weight 1.2kg each."
    res1 = run_unified_workflow(prompt)
    print(f"  Stage Reached: {res1['stage']}")
    print(f"  Status: {res1['status']}")
    print(f"  Stage 1 (Requirement): Extracted name '{res1['requirements'].get('name')}', SNP {res1['requirements'].get('snp')}")
    print(f"  Stage 2 (Retrieval): Candidates narrowed to {len(res1['candidate_packages'])} containers")
    print(f"  Stage 3 (Packing): Fits all items: {res1['fits']}, Winning Container: '{res1['best_container'].get('name')}'")
    print(f"  Volume Utilization: {res1['utilization_metrics'].get('volume_utilization_pct')}%")
    print(f"  Placed: {res1['utilization_metrics'].get('placed_count')} / {res1['utilization_metrics'].get('total_items')}")
    assert res1["stage"] == "packing_optimization"
    assert res1["fits"] is True
    assert res1["best_container"] is not None
    assert len(res1["placed_items"]) == 4

    # -------------------------------------------------------------
    # Scenario 2: Incomplete Text -> Human-In-The-Loop Trigger
    # -------------------------------------------------------------
    print("\n[SCENARIO 2] Ambiguous requirement triggering HITL")
    incomplete_prompt = "I want to ship some plastic brackets tomorrow."
    res2 = run_unified_workflow(incomplete_prompt)
    print(f"  Stage Reached: {res2['stage']}")
    print(f"  Status: {res2['status']}")
    print(f"  HITL Required: {res2['hitl_required']}")
    print(f"  HITL Clarification: {res2['hitl_reason']}")
    assert res2["hitl_required"] is True
    assert res2["stage"] == "hitl"

    # -------------------------------------------------------------
    # Scenario 3: Database Product ID (Product 1: Micro Terminal Block, SNP=64)
    # -------------------------------------------------------------
    print("\n[SCENARIO 3] SQLite Database Product auto-lookup (Product ID: 1)")
    res3 = run_unified_workflow({"product_id": 1})
    print(f"  Part: {res3['requirements'].get('name')}")
    print(f"  SNP: {res3['requirements'].get('snp')} units")
    print(f"  Winning Container: {res3['best_container'].get('name')}")
    print(f"  Best Part Orientation: {res3['best_orientation']}")
    print(f"  Fits: {res3['fits']} | Placed: {res3['utilization_metrics'].get('placed_count')} / {res3['utilization_metrics'].get('total_items')}")
    print(f"  Three.js 3D Scene Elements: {len(res3['scene_data'].get('items', []))} boxes")
    assert res3["fits"] is True
    assert res3["utilization_metrics"]["placed_count"] == 64
    assert len(res3["scene_data"]["items"]) == 64

    # -------------------------------------------------------------
    # Scenario 4: Heavy Part from Database (Product 45: Solid Counterweight Ingot, 38kg)
    # -------------------------------------------------------------
    print("\n[SCENARIO 4] Heavy Industrial Part (Product 45: 38kg, exceeding carton limit)")
    res4 = run_unified_workflow({"product_id": 45})
    print(f"  Part: {res4['requirements'].get('name')}")
    print(f"  Total Weight: {res4['metrics'].get('max_rating')} kg")
    print(f"  Winning Container: {res4['best_container'].get('name')} ({res4['best_container'].get('category')})")
    print(f"  Fits: {res4['fits']}")
    assert res4["fits"] is True
    assert res4["best_container"]["category"] in ("metal_stillage", "metal_pallet")

    # -------------------------------------------------------------
    # Scenario 5: HTTP API Endpoint (run_workflow_endpoint)
    # -------------------------------------------------------------
    print("\n[SCENARIO 5] FastAPI Endpoint run_workflow_endpoint")
    api_res = run_workflow_endpoint({"user_input": {"product_id": 2}})
    print(f"  API Status: {api_res['status']}")
    print(f"  Container: {api_res['best_container'].get('name')}")
    print(f"  Placed: {api_res['utilization_metrics'].get('placed_count')} / {api_res['utilization_metrics'].get('total_items')}")
    assert api_res["fits"] is True

    print("\n" + "=" * 80)
    print("ALL 5 UNIFIED 3-AGENT WORKFLOW SCENARIOS PASSED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()

