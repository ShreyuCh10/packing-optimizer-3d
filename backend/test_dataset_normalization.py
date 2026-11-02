import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.agents.package_recommendation import PackageRecommendation, recommend_package
from app.agents.retrieval_gathering import (
    fetch_all_candidates_from_db,
    narrow_down_packages,
)


class DatasetNormalizationTests(unittest.TestCase):
    def test_unmigrated_database_uses_authoritative_package_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty.db"
            sqlite3.connect(db_path).close()

            candidates, tables_queried = fetch_all_candidates_from_db(str(db_path))

        self.assertEqual(tables_queried, [])
        self.assertEqual(len(candidates), 41)
        package_16 = next(candidate for candidate in candidates if candidate["name"] == "Package 16")
        self.assertEqual(package_16["package_code"], "Package 16")
        self.assertEqual(package_16["inner_length_mm"], 394.0)
        self.assertEqual(package_16["max_weight_capacity_kg"], 6.4)
        self.assertIsNone(package_16["material"])
        self.assertIsNone(package_16["inventory"])
        self.assertTrue(all(not candidate["name"].startswith("BOX-") for candidate in candidates))

    def test_item_and_padded_bounding_box_utilization_are_separate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty.db"
            sqlite3.connect(db_path).close()
            candidates, _ = fetch_all_candidates_from_db(str(db_path))

        package_16 = next(candidate for candidate in candidates if candidate["name"] == "Package 16")
        metrics = {
            "effective_bounding_box_mm": {"length": 180.0, "width": 223.0, "height": 163.0},
            "total_volume_required_liters": 180 * 223 * 163 / 1_000_000,
            "total_product_volume_liters": 3.024,
            "max_rating": 4.8,
        }

        result = narrow_down_packages([package_16], metrics)

        self.assertEqual(len(result["matching_packages"]), 1)
        recommended = result["matching_packages"][0]
        self.assertEqual(recommended["volume_utilization_pct"], 17.96)
        self.assertEqual(recommended["padded_bbox_utilization_pct"], 38.9)
        self.assertEqual(recommended["wasted_volume_liters"], 13.814)
        self.assertEqual(recommended["padded_bbox_clearance_liters"], 10.295)

    def test_candidates_without_a_verified_payload_rating_are_not_recommended(self):
        candidate = {
            "package_id": "unrated",
            "package_code": "unrated",
            "name": "Unrated container",
            "category": "carton",
            "inner_length_mm": 500.0,
            "inner_width_mm": 500.0,
            "inner_height_mm": 500.0,
            "max_weight_capacity_kg": None,
            "inventory": None,
        }
        metrics = {
            "effective_bounding_box_mm": {"length": 100.0, "width": 100.0, "height": 100.0},
            "total_volume_required_liters": 1.0,
            "total_product_volume_liters": 0.5,
            "max_rating": 1.0,
        }

        result = narrow_down_packages([candidate], metrics)

        self.assertEqual(result["matching_packages"], [])

    def test_model_selection_explanation_is_composed_only_from_verified_facts(self):
        candidate = {
            "candidate_id": "Package 16",
            "package_code": "Package 16",
            "name": "Package 16",
            "category": "carton",
            "material": None,
            "volume_utilization_pct": 17.96,
            "padded_bbox_utilization_pct": 38.9,
            "wasted_volume_liters": 13.814,
            "total_packed_weight_kg": 4.8,
            "max_weight_capacity_kg": 6.4,
            "weight_margin_kg": 1.6,
            "quantity": 4,
        }
        structured_model = Mock()
        structured_model.invoke.return_value = PackageRecommendation(
            candidate_id="Package 16",
            selection_factors=["highest_item_volume_utilization"],
        )
        chat_model = Mock()
        chat_model.with_structured_output.return_value = structured_model

        with patch.dict(
            "os.environ",
            {
                "AZURE_FOUNDRY_OPENAI_BASE_URL": "https://example.invalid/v1",
                "AZURE_FOUNDRY_OPENAI_API_KEY": "test-key",
                "AZURE_FOUNDRY_OPENAI_MODEL": "gpt-5.1",
            },
        ), patch("app.agents.package_recommendation.ChatOpenAI", return_value=chat_model):
            recommendation = recommend_package([candidate])

        self.assertEqual(recommendation["selected_candidate_id"], "Package 16")
        self.assertIn("17.96% item-volume utilization", recommendation["assistant_response"])
        self.assertIn("1.6 kg margin", recommendation["assistant_response"])
        self.assertIn("does not specify its material", recommendation["assistant_response"])
        self.assertNotIn("double wall", recommendation["assistant_response"].lower())
        self.assertNotIn("fragility", recommendation["assistant_response"].lower())


if __name__ == "__main__":
    unittest.main()
