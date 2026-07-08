import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.costing import ProviderPricing, estimate_cost, normalize_token_usage


class CostingTests(unittest.TestCase):
    def test_normalizes_openai_compatible_usage_payload(self):
        usage = normalize_token_usage(
            {
                "prompt_tokens": 1200,
                "completion_tokens": 300,
                "total_tokens": 1500,
            }
        )

        self.assertEqual(usage["prompt_tokens"], 1200)
        self.assertEqual(usage["completion_tokens"], 300)
        self.assertEqual(usage["total_tokens"], 1500)

    def test_estimates_cost_from_per_million_token_pricing(self):
        pricing = ProviderPricing(
            provider_name="fake-provider",
            model="fake-model",
            input_per_1m_tokens=0.10,
            output_per_1m_tokens=0.20,
            source_url="https://example.test/pricing",
        )

        cost = estimate_cost(
            {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
            pricing,
        )

        self.assertEqual(cost["currency"], "USD")
        self.assertEqual(cost["input_cost"], 0.0001)
        self.assertEqual(cost["output_cost"], 0.0001)
        self.assertEqual(cost["total_cost"], 0.0002)
        self.assertEqual(cost["pricing_source"], "https://example.test/pricing")

    def test_missing_usage_has_zero_tokens_and_zero_cost(self):
        pricing = ProviderPricing(
            provider_name="offline",
            model="rule-based",
            input_per_1m_tokens=0.0,
            output_per_1m_tokens=0.0,
        )

        usage = normalize_token_usage(None)
        cost = estimate_cost(usage, pricing)

        self.assertEqual(usage["total_tokens"], 0)
        self.assertEqual(cost["total_cost"], 0.0)


if __name__ == "__main__":
    unittest.main()
