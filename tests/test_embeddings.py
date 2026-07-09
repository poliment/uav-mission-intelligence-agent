import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.embeddings import cosine_similarity, embed_text


class EmbeddingTests(unittest.TestCase):
    def test_embed_text_returns_deterministic_sparse_features(self):
        first = embed_text("multi UAV area search")
        second = embed_text("multi UAV area search")

        self.assertEqual(first, second)
        self.assertGreater(first["multi"], 0)
        self.assertGreater(first["area"], 0)
        self.assertGreater(first["char:uav"], 0)

    def test_cosine_similarity_prefers_related_text(self):
        query = embed_text("weak communication UAV coordination")
        related = embed_text("distributed coordination under weak communication")
        unrelated = embed_text("static no fly zone boundary")

        self.assertGreater(cosine_similarity(query, related), cosine_similarity(query, unrelated))


if __name__ == "__main__":
    unittest.main()
