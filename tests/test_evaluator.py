import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.evaluator import evaluate_plan
from uav_mission_agent.scenario_loader import load_scenario
from uav_mission_agent.workflow import run_mission_workflow


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenarios"


class EvaluatorTests(unittest.TestCase):
    def test_scores_matching_plan_with_breakdown(self):
        scenario = load_scenario(FIXTURE_DIR / "area_search_low_bandwidth.json")
        plan = run_mission_workflow(scenario.mission_text)

        result = evaluate_plan(plan, scenario)

        self.assertGreaterEqual(result.score, 0.85)
        self.assertEqual(result.breakdown["uav_count"], 1.0)
        self.assertEqual(result.breakdown["search_areas"], 1.0)
        self.assertEqual(result.breakdown["avoid_zones"], 1.0)
        self.assertGreaterEqual(result.breakdown["risk_keywords"], 0.66)
        self.assertEqual(result.scenario_id, "area_search_low_bandwidth")

    def test_penalizes_missing_required_constraints(self):
        scenario = load_scenario(FIXTURE_DIR / "area_search_low_bandwidth.json")
        weak_plan = {
            "task": {"drone_count": 1, "objectives": [], "constraints": []},
            "mission_config": {"uav_count": 1, "search_areas": [], "avoid_zones": [], "constraints": []},
            "recommendations": [],
            "risks": []
        }

        result = evaluate_plan(weak_plan, scenario)

        self.assertLess(result.score, 0.5)
        self.assertIn("uav_count", result.missing_requirements)
        self.assertIn("low_bandwidth_coordination", result.missing_requirements)


if __name__ == "__main__":
    unittest.main()

