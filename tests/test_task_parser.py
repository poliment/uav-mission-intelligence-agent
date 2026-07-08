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


if __name__ == "__main__":
    unittest.main()

