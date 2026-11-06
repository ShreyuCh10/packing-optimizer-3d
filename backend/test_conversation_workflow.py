"""Tests for backend-persisted conversational requirement gathering."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from app.agents import conversation_workflow as chat
from app.agents import requirement
from app.agents import workflow as unified_workflow
from app.api import requirement_routes


def catalog_row(product_id, name):
    return {
        "id": product_id,
        "part_name": name,
        "part_length": 100,
        "part_breadth": 50,
        "part_height": 25,
        "part_weight": 0.2,
        "part_type": "steel",
        "standard_no_of_parts": 12,
    }


class ConversationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.states = {}
        self.patches = [
            patch.object(chat, "load_conversation", side_effect=lambda key: deepcopy(self.states.get(key))),
            patch.object(chat, "save_conversation", side_effect=lambda key, value: self.states.__setitem__(key, deepcopy(value))),
            patch.object(chat, "generate_conversation_prompt", return_value="Would you like to add another catalog product?"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()

    def test_custom_product_and_dimensions_never_enter_manifest_or_optimize(self):
        extraction = {
            "items": [{
                "name": "custom bracket", "quantity": 20, "part_length": 120,
                "part_width": 80, "part_height": 50, "part_weight": 1.5,
                "catalog_reference": False,
            }],
            "assistant_message": "Which catalog product do you mean?",
            "method": "LLM",
        }
        with patch.object(chat, "gather_requirements_turn", return_value=extraction), \
             patch("app.agents.workflow.run_unified_workflow") as optimize:
            result = chat.process_chat_turn("custom", "Pack my custom bracket 20x120x80x50, 1.5 kg")

        self.assertEqual(result["action"], "conversation")
        self.assertEqual(self.states["custom"]["manifest"], [])
        self.assertEqual(self.states["custom"]["draft_items"], [])
        optimize.assert_not_called()

    def test_structured_llm_is_called_for_gathering_turn(self):
        class FakeExtractor:
            def invoke(self, _prompt):
                return requirement.RequirementTurnExtraction(
                    items=[], assistant_message="Which catalog product would you like?",
                )

        class FakeLLM:
            def with_structured_output(self, schema):
                self.schema = schema
                return FakeExtractor()

        fake_llm = FakeLLM()
        with patch.object(requirement, "llm", fake_llm):
            result = requirement.gather_requirements_turn("hello", conversation_history=[])

        self.assertEqual(result["method"], "Azure OpenAI Conversational Requirement Extractor")
        self.assertEqual(result["items"], [])
        self.assertIs(fake_llm.schema, requirement.RequirementTurnExtraction)

    def test_typo_tolerant_multi_product_ids_keep_quantities(self):
        products = {
            1: {"id": 1, "part_name": "First product"},
            2: {"id": 2, "part_name": "Second product"},
        }
        with patch.object(requirement, "get_product_by_id", side_effect=lambda product_id: products[product_id]):
            extracted = requirement._explicit_catalog_items("20 of prouduct 1 and 20 of proudct 2")

        self.assertEqual([item.product_id for item in extracted], [1, 2])
        self.assertEqual([item.quantity for item in extracted], [20, 20])

    def test_explicit_ids_override_name_only_llm_guesses(self):
        class FakeExtractor:
            def invoke(self, _prompt):
                return requirement.RequirementTurnExtraction(
                    items=[requirement.GatheredItem(name="Product 1", catalog_reference=True, quantity=20)],
                    assistant_message="I found the products.",
                )

        class FakeLLM:
            def with_structured_output(self, _schema):
                return FakeExtractor()

        with patch.object(requirement, "llm", FakeLLM()), \
             patch.object(requirement, "get_product_by_id", side_effect=lambda pid: {"id": pid, "part_name": f"Product {pid}"}):
            extracted = requirement.gather_requirements_turn(
                "20 of product 1 and 20 of product 30 and 20 of product 10"
            )

        self.assertEqual([item["product_id"] for item in extracted["items"]], [1, 30, 10])
        self.assertEqual([item["quantity"] for item in extracted["items"]], [20, 20, 20])

    def test_catalog_product_requires_confirmation_then_explicit_done_to_optimize(self):
        extraction = {
            "items": [{"product_id": 1, "name": "Catalog Bracket", "quantity": 6, "catalog_reference": True}],
            "assistant_message": "I found it.",
            "method": "LLM",
        }
        product = catalog_row(1, "Catalog Bracket")
        optimized_result = {"status": "workflow_completed_optimal_fit", "stage": "packing_optimization", "summary": "Packed all six parts.", "fits": True}
        with patch.object(chat, "gather_requirements_turn", return_value=extraction), \
             patch.object(chat, "get_product_by_id", return_value=product), \
             patch("app.agents.workflow.run_unified_workflow", return_value=optimized_result) as optimize:
            pending = chat.process_chat_turn("catalog", "Pack 6 of product 1")
            self.assertEqual(pending["action"], "confirm_product")
            self.assertEqual(pending["matched_products"][0]["quantity"], 6)
            self.assertEqual(self.states["catalog"]["manifest"], [])

            confirmed = chat.process_chat_turn("catalog", {"confirmed": True, "text": "Confirmed"})
            self.assertEqual(confirmed["status"], "awaiting_more_items")
            self.assertEqual(self.states["catalog"]["manifest"][0]["product_id"], 1)
            optimize.assert_not_called()

            done = chat.process_chat_turn("catalog", "No, that's all")
            self.assertEqual(done["action"], "optimized")
            self.assertEqual(optimize.call_args.args[0]["items"][0]["product_id"], 1)
            self.assertEqual(self.states["catalog"]["phase"], "completed")

    def test_exit_without_confirmed_manifest_never_optimizes(self):
        state = chat._new_state()
        state["phase"] = "awaiting_more_items"
        self.states["empty"] = state
        with patch("app.agents.workflow.run_unified_workflow") as optimize:
            result = chat.process_chat_turn("empty", "done")

        self.assertEqual(result["action"], "conversation")
        self.assertEqual(result["status"], "conversation_gathering")
        optimize.assert_not_called()

    def test_explicit_optimize_action_runs_confirmed_manifest_from_any_gathering_phase(self):
        state = chat._new_state()
        state["phase"] = "gathering"
        state["manifest"] = [{"product_id": 1, "part_name": "Catalog Bracket", "quantity": 2}]
        self.states["button-optimize"] = state
        optimized = {"status": "workflow_completed_optimal_fit", "action": "optimized"}
        with patch.object(chat, "_start_optimization", return_value=optimized) as start:
            result = chat.process_chat_turn(
                "button-optimize", {"action": "optimize", "text": "Optimize confirmed products"}
            )

        self.assertEqual(result["action"], "optimized")
        start.assert_called_once()

    def test_add_another_reply_takes_precedence_over_leading_no(self):
        state = chat._new_state()
        state["phase"] = "awaiting_more_items"
        state["manifest"] = [{"product_id": 1, "part_name": "Catalog Bracket", "quantity": 2}]
        self.states["another"] = state
        with patch("app.agents.workflow.run_unified_workflow") as optimize:
            result = chat.process_chat_turn("another", "No, add another product")

        self.assertEqual(result["status"], "conversation_gathering")
        self.assertEqual(self.states["another"]["phase"], "gathering")
        optimize.assert_not_called()

    def test_direct_workflow_rejects_custom_dimensions(self):
        result = unified_workflow.requirement_gathering_node({
            "user_input": {
                "name": "custom bracket", "part_length": 120, "part_width": 80,
                "part_height": 50, "part_weight": 1.5, "quantity": 20,
            },
            "conversation_history": [],
        })

        self.assertTrue(result["hitl_required"])
        self.assertFalse(result["requirement_fulfilled"])
        self.assertIsNone(result["requirements"])

    def test_structured_manifest_must_resolve_to_catalog_products(self):
        with patch.object(unified_workflow, "get_product_by_name", return_value=None):
            result = unified_workflow.requirement_gathering_node({
                "user_input": {"items": [{
                    "name": "custom bracket", "quantity": 20,
                    "part_length": 120, "part_width": 80, "part_height": 50,
                    "part_weight": 1.5,
                }]},
                "conversation_history": [],
            })

        self.assertEqual(result["status"], "product_not_found")
        self.assertTrue(result["product_not_found"])
        self.assertIsNone(result["requirements"])

    def test_cart_execute_route_runs_the_structured_manifest(self):
        workflow_result = {
            "status": "workflow_completed_optimal_fit",
            "stage": "packing_optimization",
            "fits": True,
            "requirements": {"items": [{
                "product_id": 8, "part_name": "Catalog Widget", "quantity": 3,
            }]},
        }
        request = {"user_input": {"items": [{
            "product_id": 8, "part_name": "Catalog Widget", "number_of_parts": 3,
        }]}}
        with patch("app.agents.workflow.run_unified_workflow", return_value=workflow_result) as optimize:
            result = requirement_routes.execute_workflow_endpoint(request)

        optimize.assert_called_once()
        self.assertEqual(optimize.call_args.args[0], request["user_input"])
        self.assertEqual(result["action"], "optimized")
        self.assertEqual(result["task_manifest"][0]["product_id"], 8)
        self.assertEqual(result["task_manifest"][0]["quantity"], 3)


if __name__ == "__main__":
    unittest.main()
