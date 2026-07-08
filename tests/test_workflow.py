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
        self.assertGreaterEqual(len(result["recommendations"]), 2)
        self.assertGreaterEqual(len(result["risks"]), 1)


if __name__ == "__main__":
    unittest.main()

