import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.knowledge_base import KnowledgeBase
from uav_mission_agent.workflow import run_mission_workflow


class WorkflowTests(unittest.TestCase):
    def test_retrieves_relevant_uav_knowledge(self):
        knowledge = KnowledgeBase.default()

        snippets = knowledge.retrieve("多无人机 搜索 弱通信 禁飞区", limit=2)

        self.assertEqual(len(snippets), 2)
        self.assertTrue(any("搜索" in snippet.content for snippet in snippets))
        self.assertTrue(any("弱通信" in snippet.content or "通信" in snippet.content for snippet in snippets))

    def test_workflow_returns_structured_plan_and_config(self):
        result = run_mission_workflow("使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。")

        self.assertEqual(result["task"]["drone_count"], 3)
        self.assertEqual(result["mission_config"]["uav_count"], 3)
        self.assertIn("区域A", result["mission_config"]["search_areas"])
        self.assertIn("禁飞区B", result["mission_config"]["avoid_zones"])
        self.assertGreaterEqual(len(result["retrieved_knowledge"]), 1)
        self.assertEqual(result["retrieved_knowledge"][0]["retriever"], "local-vector")
        self.assertIn("score", result["retrieved_knowledge"][0])
        self.assertIn("rank", result["retrieved_knowledge"][0])
        self.assertGreaterEqual(len(result["recommendations"]), 2)
        self.assertGreaterEqual(len(result["risks"]), 1)

    def test_workflow_uses_task_specific_planning_policy(self):
        tracking = run_mission_workflow("使用4架无人机持续跟踪目标T1，并保持多机协同。")
        replanning = run_mission_workflow("使用2架无人机巡检区域C，禁飞区D临时出现，需要重新规划航迹并避障。")

        self.assertEqual(tracking["mission_config"]["planning_policy"], "target_tracking_with_distributed_coordination")
        self.assertEqual(replanning["mission_config"]["planning_policy"], "dynamic_replanning_with_constraint_avoidance")

    def test_workflow_can_route_to_langgraph_backend(self):
        calls = {}

        def fake_langgraph_runner(text, knowledge_base=None, llm_provider=None):
            calls["text"] = text
            calls["knowledge_base"] = knowledge_base
            calls["llm_provider"] = llm_provider
            return {
                "mission_config": {"uav_count": 1},
                "agent_trace": [{"node": "task_parser_agent"}],
                "agent_review": {"ready": True},
                "graph_backend": "langgraph",
            }

        result = run_mission_workflow(
            "use 1 UAV to inspect area A",
            graph_backend="langgraph",
            langgraph_runner=fake_langgraph_runner,
        )

        self.assertEqual(calls["text"], "use 1 UAV to inspect area A")
        self.assertEqual(result["graph_backend"], "langgraph")
        self.assertNotIn("agent_trace", result)
        self.assertNotIn("agent_review", result)


if __name__ == "__main__":
    unittest.main()
