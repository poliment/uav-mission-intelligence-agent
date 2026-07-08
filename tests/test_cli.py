import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.cli import main
from uav_mission_agent.langgraph_workflow import LangGraphUnavailableError


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenarios"


class CliTests(unittest.TestCase):
    def test_benchmark_mode_prints_json_report(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            main(["--benchmark", str(FIXTURE_DIR)])

        report = json.loads(output.getvalue())
        self.assertEqual(report["summary"]["total_scenarios"], 1)
        self.assertGreaterEqual(report["summary"]["average_score"], 0.85)

    def test_trace_flag_prints_agent_trace_for_single_mission(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            main(["--trace", "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。"])

        result = json.loads(output.getvalue())
        self.assertEqual(result["agent_trace"][0]["node"], "task_parser_agent")
        self.assertTrue(result["agent_review"]["ready"])

    def test_single_mission_hides_trace_by_default(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            main(["使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。"])

        result = json.loads(output.getvalue())
        self.assertNotIn("agent_trace", result)
        self.assertNotIn("agent_review", result)

    def test_dashboard_mode_writes_html_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.html"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                main(["--dashboard", str(output_path)])

            result = json.loads(output.getvalue())
            self.assertEqual(result["dashboard"], str(output_path))
            self.assertTrue(output_path.exists())
            self.assertIn("UAV Mission Intelligence Dashboard", output_path.read_text(encoding="utf-8"))

    def test_schema_output_wraps_single_mission_result(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            main(["--schema-output", "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。"])

        result = json.loads(output.getvalue())
        self.assertEqual(result["schema_name"], "uav_mission_plan")
        self.assertTrue(result["validation"]["valid"])
        self.assertEqual(result["data"]["mission_config"]["uav_count"], 3)

    def test_langgraph_backend_reports_missing_dependency_from_cli(self):
        error = io.StringIO()

        with patch(
            "uav_mission_agent.cli.run_mission_workflow",
            side_effect=LangGraphUnavailableError("LangGraph backend requires pip install langgraph"),
        ):
            with self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(error):
                    main(["--graph-backend", "langgraph", "use 1 UAV to inspect area A"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("LangGraph backend requires", error.getvalue())

    def test_trajectory_intent_mode_reads_json_file(self):
        trajectory = [
            {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 100, "speed": 4, "heading": 0, "roll": 10, "pitch": 0, "yaw": 0},
            {"timestamp": 10, "latitude": 30.0001, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 160, "roll": -10, "pitch": 0, "yaw": 160},
            {"timestamp": 20, "latitude": 30.0002, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 320, "roll": 12, "pitch": 0, "yaw": 320},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "trajectory.json"
            path.write_text(json.dumps(trajectory), encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                main(["--trajectory-intent", str(path)])

        result = json.loads(output.getvalue())
        self.assertEqual(result["intent"], "loitering")
        self.assertIn("summary", result)
        self.assertIn("evidence", result)


if __name__ == "__main__":
    unittest.main()
