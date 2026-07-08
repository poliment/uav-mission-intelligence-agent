import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.benchmark import run_benchmark
from uav_mission_agent.scenario_loader import load_scenarios


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenarios"


class BenchmarkTests(unittest.TestCase):
    def test_runs_benchmark_and_returns_aggregate_metrics(self):
        scenarios = load_scenarios(FIXTURE_DIR)

        report = run_benchmark(scenarios)

        self.assertEqual(report["summary"]["total_scenarios"], 1)
        self.assertGreaterEqual(report["summary"]["average_score"], 0.85)
        self.assertEqual(report["results"][0]["scenario_id"], "area_search_low_bandwidth")
        self.assertIn("score", report["results"][0])


if __name__ == "__main__":
    unittest.main()

