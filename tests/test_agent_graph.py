import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.agent_graph import run_agent_workflow


class AgentGraphTests(unittest.TestCase):
    def test_agent_workflow_returns_ordered_node_trace(self):
        result = run_agent_workflow("使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。")

        self.assertEqual(
            [step["node"] for step in result["agent_trace"]],
            [
                "task_parser_agent",
                "knowledge_retriever_agent",
                "mission_planner_agent",
                "mission_reviewer_agent",
            ],
        )
        self.assertEqual(result["agent_trace"][0]["status"], "ok")
        self.assertIn("raw_request", result["agent_trace"][0]["input_keys"])
        self.assertIn("task", result["agent_trace"][0]["output_keys"])
        self.assertIn("mission_config", result)

    def test_agent_review_reports_ready_plan_for_valid_mission(self):
        result = run_agent_workflow("使用4架无人机持续跟踪目标T1，并保持多机协同。")

        review = result["agent_review"]
        self.assertTrue(review["ready"])
        self.assertEqual(review["warning_count"], 0)
        self.assertIn("target_tracking", result["mission_config"]["objectives"])
        self.assertEqual(
            result["mission_config"]["planning_policy"],
            "target_tracking_with_distributed_coordination",
        )


if __name__ == "__main__":
    unittest.main()

