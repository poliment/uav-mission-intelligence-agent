import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.benchmark_v2 import BenchmarkProviderConfig, run_benchmark_v2
from uav_mission_agent.costing import ProviderPricing
from uav_mission_agent.scenario_loader import load_scenarios


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenarios"


class FakeBenchmarkProvider:
    provider_name = "fake-llm"
    model = "fake-model"

    def __init__(self):
        self.last_usage = {
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
        }

    def generate_plan(self, *, task, retrieved_knowledge, baseline_plan, output_schema):
        return {
            "recommendations": baseline_plan["recommendations"],
            "risks": baseline_plan["risks"],
            "mission_config": baseline_plan["mission_config"],
        }


class BenchmarkV2Tests(unittest.TestCase):
    def test_runs_offline_benchmark_v2_with_provider_and_difficulty_summaries(self):
        report = run_benchmark_v2(load_scenarios(FIXTURE_DIR))

        self.assertEqual(report["summary"]["benchmark_version"], "2.0")
        self.assertEqual(report["summary"]["total_scenarios"], 1)
        self.assertEqual(report["summary"]["provider_count"], 1)
        self.assertEqual(report["summary"]["total_runs"], 1)
        self.assertGreaterEqual(report["summary"]["average_score"], 0.85)
        self.assertEqual(report["results"][0]["provider_label"], "offline")
        self.assertEqual(report["provider_comparison"][0]["provider_label"], "offline")
        self.assertEqual(report["difficulty_summary"][0]["difficulty"], "medium")
        self.assertEqual(report["results"][0]["token_usage"]["total_tokens"], 0)

    def test_benchmark_v2_estimates_live_provider_cost_from_usage(self):
        pricing = ProviderPricing(
            provider_name="fake-llm",
            model="fake-model",
            input_per_1m_tokens=1.0,
            output_per_1m_tokens=2.0,
        )
        config = BenchmarkProviderConfig(
            label="fake-live",
            provider_name="fake-llm",
            model="fake-model",
            pricing=pricing,
        )

        report = run_benchmark_v2(
            load_scenarios(FIXTURE_DIR),
            provider_configs=[config],
            provider_factory=lambda *args, **kwargs: FakeBenchmarkProvider(),
        )

        result = report["results"][0]
        self.assertEqual(result["provider_label"], "fake-live")
        self.assertEqual(result["provider_name"], "fake-llm")
        self.assertEqual(result["model"], "fake-model")
        self.assertEqual(result["token_usage"]["prompt_tokens"], 200)
        self.assertEqual(result["token_usage"]["completion_tokens"], 100)
        self.assertEqual(result["estimated_cost"]["total_cost"], 0.0004)
        self.assertEqual(report["summary"]["estimated_total_cost"], 0.0004)
        self.assertEqual(report["provider_comparison"][0]["estimated_total_cost"], 0.0004)


if __name__ == "__main__":
    unittest.main()
