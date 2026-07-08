import json
import sys
import tempfile
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

    def test_loads_scenario_arrays_from_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "scenarios.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "id": "array_case_1",
                            "name": "Array case 1",
                            "difficulty": "easy",
                            "mission_text": "使用1架无人机搜索区域A。",
                            "expected": _valid_expected(),
                            "challenge_types": ["ambiguous_instruction"],
                        },
                        {
                            "id": "array_case_2",
                            "name": "Array case 2",
                            "difficulty": "medium",
                            "mission_text": "使用2架无人机搜索区域B。",
                            "expected": _valid_expected(uav_count=2, search_areas=["区域B"]),
                            "challenge_types": ["mixed_zh_en"],
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            scenarios = load_scenarios(tmpdir)

        self.assertEqual([scenario.scenario_id for scenario in scenarios], ["array_case_1", "array_case_2"])

    def test_rejects_scenario_missing_required_fields(self):
        with self.assertRaisesRegex(ValueError, "expected"):
            load_scenario(FIXTURE_DIR / "invalid_missing_expected.json")


def _valid_expected(
    uav_count: int = 1,
    search_areas: list[str] | None = None,
) -> dict:
    return {
        "uav_count": uav_count,
        "search_areas": search_areas or ["区域A"],
        "avoid_zones": [],
        "objectives": ["area_search"],
        "constraints": [],
        "risk_keywords": [],
    }


if __name__ == "__main__":
    unittest.main()
