import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uav_mission_agent.scenario_loader import load_scenarios


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "data" / "scenarios"
REQUIRED_CHALLENGE_TYPES = {
    "ambiguous_instruction",
    "conflicting_constraints",
    "missing_uav_count",
    "incomplete_area_boundary",
    "overlapping_no_fly_and_target_area",
    "weak_comm_tracking_replan_combo",
    "mixed_zh_en",
    "noisy_expression",
}


class BenchmarkDatasetTests(unittest.TestCase):
    def test_public_benchmark_has_enough_hard_scenarios(self):
        scenarios = load_scenarios(SCENARIO_DIR)

        self.assertGreaterEqual(len(scenarios), 20)
        self.assertLessEqual(len(scenarios), 50)

    def test_public_benchmark_covers_required_challenge_types(self):
        scenarios = _load_raw_scenarios()
        covered = {
            challenge
            for scenario in scenarios
            for challenge in scenario.get("challenge_types", [])
        }

        self.assertTrue(REQUIRED_CHALLENGE_TYPES <= covered)

    def test_public_benchmark_scenarios_declare_challenge_types(self):
        for scenario in _load_raw_scenarios():
            self.assertIn("challenge_types", scenario, scenario["id"])
            self.assertTrue(scenario["challenge_types"], scenario["id"])


def _load_raw_scenarios() -> list[dict]:
    scenarios: list[dict] = []
    for path in sorted(SCENARIO_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            scenarios.extend(data)
        else:
            scenarios.append(data)
    return scenarios


if __name__ == "__main__":
    unittest.main()
