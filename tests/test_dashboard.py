import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.dashboard import build_dashboard_html, write_dashboard


SCENARIO_DIR = Path(__file__).resolve().parents[1] / "data" / "scenarios"
MISSION_TEXT = "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"


class DashboardTests(unittest.TestCase):
    def test_build_dashboard_html_contains_core_visual_sections(self):
        html = build_dashboard_html(MISSION_TEXT, SCENARIO_DIR)

        self.assertIn("UAV Mission Intelligence Dashboard", html)
        self.assertIn('id="mission-input"', html)
        self.assertIn("task_parser_agent", html)
        self.assertIn("knowledge_retriever_agent", html)
        self.assertIn("mission_planner_agent", html)
        self.assertIn("mission_reviewer_agent", html)
        self.assertIn("coverage_first_with_constraint_avoidance", html)
        self.assertIn("average_score", html)
        self.assertIn("area_search_low_bandwidth", html)
        self.assertIn("score-bar", html)

    def test_write_dashboard_creates_local_html_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.html"

            written = write_dashboard(output_path, MISSION_TEXT, SCENARIO_DIR)

            self.assertEqual(written, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("<!doctype html>", output_path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
