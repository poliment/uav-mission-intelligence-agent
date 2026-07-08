import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.schemas import build_schema_output, validate_mission_plan
from uav_mission_agent.workflow import run_mission_workflow


class SchemaOutputTests(unittest.TestCase):
    def test_build_schema_output_wraps_plan_with_validation_metadata(self):
        plan = run_mission_workflow("使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。")

        output = build_schema_output(plan)

        self.assertEqual(output["schema_name"], "uav_mission_plan")
        self.assertEqual(output["schema_version"], "1.0")
        self.assertTrue(output["validation"]["valid"])
        self.assertEqual(output["validation"]["errors"], [])
        self.assertIn("mission_config", output["schema"]["required"])
        self.assertEqual(output["data"]["mission_config"]["uav_count"], 3)

    def test_validate_mission_plan_reports_missing_required_fields(self):
        validation = validate_mission_plan({"task": {}, "recommendations": [], "risks": []})

        self.assertFalse(validation["valid"])
        self.assertIn("missing required field: mission_config", validation["errors"])


if __name__ == "__main__":
    unittest.main()
