import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
MISSION_ASSET = REPO_ROOT / "docs" / "assets" / "mission-execution-visualization.svg"


class ReadmeAssetsTests(unittest.TestCase):
    def test_readme_references_mission_execution_visualization_asset(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("docs/assets/mission-execution-visualization.svg", readme)

    def test_mission_execution_visualization_asset_exists(self):
        self.assertTrue(MISSION_ASSET.exists())
        svg = MISSION_ASSET.read_text(encoding="utf-8")
        self.assertIn("Mission Execution Visualization", svg)
        self.assertIn("UAV-1", svg)
        self.assertIn("No-Fly Zone", svg)

    def test_readme_documents_vector_rag_backends(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("local vector RAG", readme)
        self.assertIn("rag-faiss", readme)
        self.assertIn("rag-chroma", readme)
        self.assertNotIn("RAG-ready; the local knowledge retriever can later be replaced", readme)

    def test_readme_documents_interactive_demo(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("Interactive Demo / 交互式 Demo", readme)
        self.assertIn('pip install -e ".[demo]"', readme)
        self.assertIn("uav-mission-agent-demo --host 127.0.0.1 --port 8000", readme)
        self.assertIn("uav-mission-agent-demo --env-file D:\\epacode\\working\\.secrets\\deepseek.env", readme)
        self.assertIn("Agent trace", readme)
        self.assertIn("provider comparison", readme)

    def test_readme_documents_swarm_algorithm_layer(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("Swarm upgrade status", readme)
        self.assertIn("swarm_algorithms.py", readme)
        self.assertIn("A* path planning", readme)

    def test_readme_documents_swarm_coordinator_stage(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("Swarm Coordinator", readme)
        self.assertIn("swarm_coordinator.py", readme)
        self.assertIn("examples/swarm_coordinator_demo.py", readme)
        self.assertIn("Dynamic replanning / 动态重规划", readme)

    def test_readme_documents_multi_agent_collaboration_stage(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("Multi-Agent Collaboration", readme)
        self.assertIn("swarm_dialogue.py", readme)
        self.assertIn("examples/swarm_dialogue_demo.py", readme)
        self.assertIn("agent message timeline", readme)


if __name__ == "__main__":
    unittest.main()
