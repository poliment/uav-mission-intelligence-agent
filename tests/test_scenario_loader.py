import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.scenario_loader import load_scenario, load_scenarios


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenarios"


class ScenarioLoaderTests(unittest.TestCase):
    def test_loads_valid_mission_scenario(self):
        scenario = load_scenario(FIXTURE_DIR / "area_search_low_bandwidth.json")

        self.assertEqual(scenario.scenario_id, "area_search_low_bandwidth")
        self.assertEqual(scenario.expected["uav_count"], 3)
        self.assertIn("area_search", scenario.expected["objectives"])
        self.assertIn("弱通信", scenario.expected["risk_keywords"])

    def test_loads_all_valid_scenarios_from_directory(self):
        scenarios = load_scenarios(FIXTURE_DIR)

        self.assertEqual([scenario.scenario_id for scenario in scenarios], ["area_search_low_bandwidth"])

    def test_rejects_scenario_missing_required_fields(self):
        with self.assertRaisesRegex(ValueError, "expected"):
            load_scenario(FIXTURE_DIR / "invalid_missing_expected.json")


if __name__ == "__main__":
    unittest.main()

