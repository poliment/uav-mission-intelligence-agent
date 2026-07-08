import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.agent_graph import run_agent_workflow
from uav_mission_agent.mission_visualization import (
    render_mission_execution_svg,
    write_mission_visualization_asset,
)


MISSION_TEXT = "Use 3 UAVs to search area_A, avoid NFZ_B, track target T1, weak comm, replan if blocked."


class MissionVisualizationTests(unittest.TestCase):
    def test_render_mission_execution_svg_contains_operational_scene(self):
        plan = run_agent_workflow(MISSION_TEXT)

        svg = render_mission_execution_svg(plan)

        self.assertIn("<svg", svg)
        self.assertIn("Mission Execution Visualization", svg)
        self.assertIn("Operating Boundary", svg)
        self.assertIn("Search Area", svg)
        self.assertIn("No-Fly Zone", svg)
        self.assertIn("Target Point", svg)
        self.assertIn("Planned Route", svg)
        self.assertIn("Replanned Route", svg)
        self.assertIn("Coverage Path", svg)
        self.assertIn("Weak Communication", svg)
        self.assertIn("UAV-1", svg)
        self.assertIn("UAV-2", svg)
        self.assertIn("UAV-3", svg)

    def test_write_mission_visualization_asset_writes_svg_file(self):
        plan = run_agent_workflow(MISSION_TEXT)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "mission.svg"

            written = write_mission_visualization_asset(output_path, plan)

            self.assertEqual(written, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("<svg", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
