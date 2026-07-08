import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.agent_graph import run_agent_workflow
from uav_mission_agent.llm_provider import LLMProviderError, OpenAICompatibleProvider, build_llm_provider


class FakePlanningProvider:
    provider_name = "fake-provider"
    model = "fake-model"

    def generate_plan(self, *, task, retrieved_knowledge, baseline_plan, output_schema):
        return {
            "recommendations": ["LLM建议：优先完成区域A覆盖搜索，并对禁飞区B设置硬约束。"],
            "risks": ["LLM风险：弱通信条件下需要考虑状态同步延迟。"],
            "mission_config": {
                **baseline_plan["mission_config"],
                "planning_policy": "llm_refined_coverage_policy",
            },
        }


class InvalidPlanningProvider:
    provider_name = "invalid-provider"
    model = "invalid-model"

    def generate_plan(self, *, task, retrieved_knowledge, baseline_plan, output_schema):
        return {
            "recommendations": "not-a-list",
            "risks": [],
            "mission_config": [],
        }


class SchemaBreakingProvider:
    provider_name = "schema-breaking-provider"
    model = "schema-breaking-model"

    def generate_plan(self, *, task, retrieved_knowledge, baseline_plan, output_schema):
        return {
            "recommendations": ["Keep the plan structured."],
            "risks": ["Validate model-provided configuration before use."],
            "mission_config": {
                **baseline_plan["mission_config"],
                "uav_count": "three",
            },
        }


class LLMProviderTests(unittest.TestCase):
    def test_agent_workflow_can_use_injected_llm_provider(self):
        result = run_agent_workflow(
            "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。",
            llm_provider=FakePlanningProvider(),
        )

        self.assertEqual(result["recommendations"][0], "LLM建议：优先完成区域A覆盖搜索，并对禁飞区B设置硬约束。")
        self.assertEqual(result["mission_config"]["planning_policy"], "llm_refined_coverage_policy")
        self.assertEqual(result["llm_metadata"]["provider"], "fake-provider")
        self.assertEqual(result["llm_metadata"]["model"], "fake-model")
        self.assertTrue(result["schema_validation"]["valid"])

    def test_agent_workflow_rejects_invalid_llm_provider_output(self):
        with self.assertRaises(LLMProviderError):
            run_agent_workflow(
                "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。",
                llm_provider=InvalidPlanningProvider(),
            )

    def test_agent_workflow_rejects_schema_breaking_llm_provider_output(self):
        with self.assertRaisesRegex(LLMProviderError, "schema validation"):
            run_agent_workflow(
                "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。",
                llm_provider=SchemaBreakingProvider(),
            )

    def test_openai_compatible_provider_parses_structured_json_response(self):
        captured = {}

        def fake_transport(*, url, headers, payload, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = payload
            captured["timeout"] = timeout
            return {
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 40,
                    "total_tokens": 140,
                },
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"recommendations":["LLM规划建议"],'
                                '"risks":["LLM风险说明"],'
                                '"mission_config":{"uav_count":2,"planning_policy":"llm_policy"}}'
                            )
                        }
                    }
                ]
            }

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            model="test-model",
            base_url="https://example.test/v1",
            transport=fake_transport,
            timeout=12,
        )

        result = provider.generate_plan(
            task={"raw_request": "使用2架无人机搜索区域A。", "drone_count": 2},
            retrieved_knowledge=[],
            baseline_plan={"mission_config": {"uav_count": 2}},
            output_schema={"schema_name": "uav_mission_plan"},
        )

        self.assertEqual(result["recommendations"], ["LLM规划建议"])
        self.assertEqual(result["risks"], ["LLM风险说明"])
        self.assertEqual(result["mission_config"]["planning_policy"], "llm_policy")
        self.assertEqual(captured["url"], "https://example.test/v1/chat/completions")
        self.assertEqual(captured["payload"]["model"], "test-model")
        self.assertEqual(captured["payload"]["max_tokens"], 1200)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(captured["timeout"], 12)
        self.assertEqual(provider.last_usage["prompt_tokens"], 100)
        self.assertEqual(provider.last_usage["completion_tokens"], 40)
        self.assertEqual(provider.last_usage["total_tokens"], 140)

    def test_openai_compatible_provider_falls_back_to_curl_transport(self):
        def failing_urllib_transport(*, url, headers, payload, timeout):
            raise LLMProviderError("LLM provider request failed: SSL EOF")

        def fake_curl_transport(*, url, headers, payload, timeout):
            return {
                "usage": {
                    "prompt_tokens": 80,
                    "completion_tokens": 20,
                    "total_tokens": 100,
                },
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"recommendations":["Fallback transport plan"],'
                                '"risks":["Fallback transport risk"],'
                                '"mission_config":{"uav_count":1,"planning_policy":"fallback_policy"}}'
                            )
                        }
                    }
                ],
            }

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            model="test-model",
            base_url="https://example.test/v1",
        )

        with patch("uav_mission_agent.llm_provider._urllib_transport", side_effect=failing_urllib_transport):
            with patch("uav_mission_agent.llm_provider._curl_transport", side_effect=fake_curl_transport):
                result = provider.generate_plan(
                    task={"raw_request": "use 1 UAV", "drone_count": 1},
                    retrieved_knowledge=[],
                    baseline_plan={"mission_config": {"uav_count": 1}},
                    output_schema={"schema_name": "uav_mission_plan"},
                )

        self.assertEqual(result["recommendations"], ["Fallback transport plan"])
        self.assertEqual(provider.last_usage["total_tokens"], 100)
        self.assertEqual(provider.last_response_metadata["transport"], "curl")

    def test_provider_factory_requires_api_key_for_openai_compatible_provider(self):
        with self.assertRaises(LLMProviderError):
            build_llm_provider("openai-compatible", api_key_env="MISSING_TEST_API_KEY")

    def test_provider_factory_supports_deepseek_alias(self):
        provider = build_llm_provider("deepseek", api_key="test-key")

        self.assertIsInstance(provider, OpenAICompatibleProvider)
        self.assertEqual(provider.provider_name, "deepseek")
        self.assertEqual(provider.base_url, "https://api.deepseek.com")
        self.assertEqual(provider.model, "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()
