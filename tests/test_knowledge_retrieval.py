import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.knowledge_base import KnowledgeBase
from uav_mission_agent.models import KnowledgeSnippet
from uav_mission_agent.retrievers import build_retriever


class KnowledgeRetrievalMetadataTests(unittest.TestCase):
    def test_knowledge_snippet_serializes_retrieval_metadata(self):
        snippet = KnowledgeSnippet(
            topic="weak_communication",
            content="Use distributed coordination under weak communication.",
            tags=["weak", "communication"],
            score=0.75,
            rank=1,
            retriever="local-vector",
            matched_tags=["weak"],
        )

        data = snippet.to_dict()

        self.assertEqual(data["score"], 0.75)
        self.assertEqual(data["rank"], 1)
        self.assertEqual(data["retriever"], "local-vector")
        self.assertEqual(data["matched_tags"], ["weak"])


class RetrieverBackendTests(unittest.TestCase):
    def test_local_vector_retriever_returns_ranked_metadata(self):
        snippets = [
            KnowledgeSnippet("coverage", "Area search coverage planning", ["area_search", "coverage"]),
            KnowledgeSnippet("coordination", "Weak communication distributed coordination", ["weak_comm", "distributed"]),
            KnowledgeSnippet("risk", "Battery risk and collision risk", ["risk"]),
        ]
        retriever = build_retriever("local-vector", snippets)

        results = retriever.retrieve("weak communication coordination", limit=2)

        self.assertEqual(results[0].topic, "coordination")
        self.assertEqual(results[0].rank, 1)
        self.assertEqual(results[0].retriever, "local-vector")
        self.assertGreater(results[0].score, 0)
        self.assertEqual(results[0].matched_tags, [])
        self.assertEqual(len(results), 2)

    def test_keyword_retriever_remains_available(self):
        snippets = [
            KnowledgeSnippet("coverage", "Area search coverage planning", ["area_search"]),
            KnowledgeSnippet("coordination", "Weak communication distributed coordination", ["weak_comm"]),
        ]
        retriever = build_retriever("keyword", snippets)

        results = retriever.retrieve("area_search", limit=1)

        self.assertEqual(results[0].topic, "coverage")
        self.assertEqual(results[0].retriever, "keyword")
        self.assertEqual(results[0].matched_tags, ["area_search"])

    def test_unknown_retriever_backend_fails_clearly(self):
        with self.assertRaisesRegex(ValueError, "unsupported retriever backend: made-up"):
            build_retriever("made-up", [])

    def test_optional_backends_report_install_hints_when_missing(self):
        with self.assertRaisesRegex(RuntimeError, "rag-faiss"):
            build_retriever("faiss", [])
        with self.assertRaisesRegex(RuntimeError, "rag-chroma"):
            build_retriever("chroma", [])


class KnowledgeBaseVectorIntegrationTests(unittest.TestCase):
    def test_default_knowledge_base_uses_local_vector_metadata(self):
        snippets = KnowledgeBase.default().retrieve("weak communication coordination", limit=2)

        self.assertEqual(snippets[0].retriever, "local-vector")
        self.assertEqual(snippets[0].rank, 1)
        self.assertIsInstance(snippets[0].score, float)

    def test_from_snippets_can_select_keyword_backend(self):
        knowledge = KnowledgeBase.from_snippets(
            [
                KnowledgeSnippet("coverage", "Area search coverage planning", ["area_search"]),
                KnowledgeSnippet("coordination", "Weak communication distributed coordination", ["weak_comm"]),
            ],
            retriever_backend="keyword",
        )

        snippets = knowledge.retrieve("area_search", limit=1)

        self.assertEqual(snippets[0].topic, "coverage")
        self.assertEqual(snippets[0].retriever, "keyword")


class PackagingConfigTests(unittest.TestCase):
    def test_pyproject_declares_optional_rag_extras(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('rag-faiss = ["faiss-cpu>=1.8"]', pyproject)
        self.assertIn('rag-chroma = ["chromadb>=0.5"]', pyproject)
        self.assertIn('"faiss-cpu>=1.8"', pyproject)
        self.assertIn('"chromadb>=0.5"', pyproject)


if __name__ == "__main__":
    unittest.main()
