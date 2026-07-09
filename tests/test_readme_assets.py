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


if __name__ == "__main__":
    unittest.main()
