import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.task_parser import parse_task


class TaskParserTests(unittest.TestCase):
    def test_extracts_chinese_uav_mission_fields(self):
        task = parse_task("使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。")

        self.assertEqual(task.drone_count, 3)
        self.assertIn("区域A", task.search_areas)
        self.assertIn("禁飞区B", task.avoid_zones)
        self.assertIn("area_search", task.objectives)
        self.assertIn("suspicious_target_search", task.objectives)
        self.assertIn("low_bandwidth_coordination", task.constraints)

    def test_extracts_replan_and_target_tracking_intent(self):
        replan_task = parse_task("使用2架无人机巡检区域C，禁飞区D临时出现，需要重新规划航迹并避障。")
        tracking_task = parse_task("使用4架无人机持续跟踪目标T1，并保持多机协同。")

        self.assertEqual(replan_task.avoid_zones, ["禁飞区D"])
        self.assertIn("replanning", replan_task.objectives)
        self.assertIn("obstacle_avoidance", replan_task.constraints)
        self.assertIn("target_tracking", tracking_task.objectives)
        self.assertIn("multi_uav_coordination", tracking_task.constraints)


if __name__ == "__main__":
    unittest.main()
