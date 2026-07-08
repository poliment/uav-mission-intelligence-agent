import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.langgraph_workflow import LangGraphUnavailableError, run_langgraph_workflow


class FakeCompiledGraph:
    def __init__(self, graph):
        self.graph = graph

    def invoke(self, state):
        for node_name in self.graph.execution_order:
            state = self.graph.node_functions[node_name](state)
        return state


class FakeStateGraph:
    def __init__(self, state_type):
        self.state_type = state_type
        self.nodes = []
        self.node_functions = {}
        self.edges = []
        self.execution_order = []
        self.compiled = False

    def add_node(self, name, func):
        self.nodes.append(name)
        self.node_functions[name] = func

    def add_edge(self, source, target):
        self.edges.append((source, target))
        if source != "START" and target != "END":
            self.execution_order.append(target)
        elif source == "START":
            self.execution_order.append(target)

    def compile(self):
        self.compiled = True
        return FakeCompiledGraph(self)


class FakeLangGraphAPI:
    START = "START"
    END = "END"

    def __init__(self):
        self.graph = None

    def StateGraph(self, state_type):
        self.graph = FakeStateGraph(state_type)
        return self.graph


class LangGraphWorkflowTests(unittest.TestCase):
    def test_langgraph_backend_uses_stategraph_nodes_in_order(self):
        fake_api = FakeLangGraphAPI()

        result = run_langgraph_workflow(
            "use 3 UAVs to search area A",
            graph_api=fake_api,
        )

        self.assertEqual(
            fake_api.graph.nodes,
            [
                "task_parser_agent",
                "knowledge_retriever_agent",
                "mission_planner_agent",
                "mission_reviewer_agent",
            ],
        )
        self.assertEqual(
            fake_api.graph.edges,
            [
                ("START", "task_parser_agent"),
                ("task_parser_agent", "knowledge_retriever_agent"),
                ("knowledge_retriever_agent", "mission_planner_agent"),
                ("mission_planner_agent", "mission_reviewer_agent"),
                ("mission_reviewer_agent", "END"),
            ],
        )
        self.assertTrue(fake_api.graph.compiled)
        self.assertEqual(result["graph_backend"], "langgraph")
        self.assertIn("mission_config", result)
        self.assertIn("schema_validation", result)

    def test_langgraph_backend_reports_missing_dependency(self):
        with patch(
            "uav_mission_agent.langgraph_workflow._load_langgraph_api",
            side_effect=LangGraphUnavailableError("LangGraph backend requires pip install langgraph"),
        ):
            with self.assertRaisesRegex(LangGraphUnavailableError, "pip install"):
                run_langgraph_workflow("use 1 UAV to inspect area A", graph_api=None)


if __name__ == "__main__":
    unittest.main()
