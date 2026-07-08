import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.cli import main


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


if __name__ == "__main__":
    unittest.main()
