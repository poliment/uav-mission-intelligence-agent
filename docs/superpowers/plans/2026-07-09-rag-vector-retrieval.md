# RAG Vector Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the keyword-only knowledge retriever with a default offline vector RAG layer and optional FAISS/Chroma adapter boundaries.

**Architecture:** Keep `KnowledgeBase.retrieve(query, limit=3)` stable for the agent workflow. Add deterministic sparse embeddings and retriever backends behind the facade, with local vector retrieval as the default and keyword retrieval retained as a fallback/comparison backend.

**Tech Stack:** Python 3.10+, standard library only for default execution, optional `faiss-cpu>=1.8`, optional `chromadb>=0.5`, `unittest`.

## Global Constraints

- Keep `KnowledgeBase.retrieve(query, limit=3)` as the stable public retrieval API for the agent workflow.
- Add a deterministic local vector retriever that works without network access, API keys, or third-party packages.
- Do not require FAISS, Chroma, sentence-transformers, OpenAI embeddings, or any network embedding API for default execution.
- Do not add persistent vector database files in this step.
- Do not make unit tests depend on installed FAISS or Chroma packages.
- Do not call external services during tests.
- Public project positioning remains technical and project-oriented, not job-search-oriented.

---

### Task 1: Retrieval Metadata And Deterministic Embeddings

**Files:**
- Modify: `src/uav_mission_agent/models.py`
- Create: `src/uav_mission_agent/embeddings.py`
- Test: `tests/test_embeddings.py`
- Test: `tests/test_knowledge_retrieval.py`

**Interfaces:**
- Produces: `embed_text(text: str) -> dict[str, float]`
- Produces: `cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float`
- Produces: `KnowledgeSnippet(topic: str, content: str, tags: list[str], score: float | None = None, rank: int | None = None, retriever: str | None = None, matched_tags: list[str] | None = None)`

- [ ] **Step 1: Write failing embedding tests**

Create `tests/test_embeddings.py`:

```python
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
```

- [ ] **Step 2: Run embedding tests to verify they fail**

Run: `python -B -m unittest tests.test_embeddings -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'uav_mission_agent.embeddings'`.

- [ ] **Step 3: Implement deterministic sparse embeddings**

Create `src/uav_mission_agent/embeddings.py`:

```python
from __future__ import annotations

import math
import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


def embed_text(text: str) -> dict[str, float]:
    features: dict[str, float] = {}
    normalized = text.lower()
    tokens = TOKEN_PATTERN.findall(normalized)
    for token in tokens:
        features[token] = features.get(token, 0.0) + 1.0
        if len(token) >= 3:
            for index in range(len(token) - 2):
                key = f"char:{token[index:index + 3]}"
                features[key] = features.get(key, 0.0) + 0.5
    return _l2_normalize(features)


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return round(sum(value * right.get(key, 0.0) for key, value in left.items()), 6)


def _l2_normalize(features: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in features.values()))
    if norm == 0:
        return {}
    return {key: value / norm for key, value in features.items()}
```

- [ ] **Step 4: Run embedding tests to verify they pass**

Run: `python -B -m unittest tests.test_embeddings -v`

Expected: PASS with 2 tests.

- [ ] **Step 5: Write failing metadata test**

Create `tests/test_knowledge_retrieval.py`:

```python
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.models import KnowledgeSnippet


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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run metadata test to verify it fails**

Run: `python -B -m unittest tests.test_knowledge_retrieval.KnowledgeRetrievalMetadataTests.test_knowledge_snippet_serializes_retrieval_metadata -v`

Expected: FAIL with `TypeError: KnowledgeSnippet.__init__() got an unexpected keyword argument 'score'`.

- [ ] **Step 7: Extend `KnowledgeSnippet`**

Modify `src/uav_mission_agent/models.py`:

```python
@dataclass
class KnowledgeSnippet:
    topic: str
    content: str
    tags: list[str]
    score: float | None = None
    rank: int | None = None
    retriever: str | None = None
    matched_tags: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["matched_tags"] = self.matched_tags or []
        return data
```

- [ ] **Step 8: Run metadata and embedding tests**

Run: `python -B -m unittest tests.test_embeddings tests.test_knowledge_retrieval -v`

Expected: PASS.

### Task 2: Retriever Backends

**Files:**
- Create: `src/uav_mission_agent/retrievers.py`
- Modify: `tests/test_knowledge_retrieval.py`

**Interfaces:**
- Consumes: `embed_text(text: str) -> dict[str, float]`
- Consumes: `cosine_similarity(left, right) -> float`
- Produces: `OptionalDependencyError(RuntimeError)`
- Produces: `build_retriever(backend: str, snippets: list[KnowledgeSnippet]) -> Retriever`
- Produces: retrievers with `retrieve(query: str, limit: int) -> list[KnowledgeSnippet]`

- [ ] **Step 1: Add failing local vector retriever test**

Append to `tests/test_knowledge_retrieval.py`:

```python
from uav_mission_agent.retrievers import build_retriever


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
```

- [ ] **Step 2: Run retriever tests to verify they fail**

Run: `python -B -m unittest tests.test_knowledge_retrieval -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'uav_mission_agent.retrievers'`.

- [ ] **Step 3: Implement retriever backends**

Create `src/uav_mission_agent/retrievers.py`:

```python
from __future__ import annotations

import re
from dataclasses import replace
from typing import Protocol

from .embeddings import cosine_similarity, embed_text
from .models import KnowledgeSnippet


class OptionalDependencyError(RuntimeError):
    pass


class Retriever(Protocol):
    backend_name: str

    def retrieve(self, query: str, limit: int) -> list[KnowledgeSnippet]:
        raise NotImplementedError


def build_retriever(backend: str, snippets: list[KnowledgeSnippet]) -> Retriever:
    normalized = (backend or "local-vector").strip().lower()
    if normalized in {"local-vector", "vector", "local"}:
        return LocalVectorRetriever(snippets)
    if normalized in {"keyword", "keyword-score"}:
        return KeywordRetriever(snippets)
    if normalized == "faiss":
        return FaissRetriever(snippets)
    if normalized == "chroma":
        return ChromaRetriever(snippets)
    raise ValueError(f"unsupported retriever backend: {backend}")


class LocalVectorRetriever:
    backend_name = "local-vector"

    def __init__(self, snippets: list[KnowledgeSnippet]):
        self._snippets = list(snippets)
        self._vectors = [embed_text(_snippet_text(snippet)) for snippet in self._snippets]

    def retrieve(self, query: str, limit: int) -> list[KnowledgeSnippet]:
        query_vector = embed_text(query)
        scored = []
        for index, snippet in enumerate(self._snippets):
            score = cosine_similarity(query_vector, self._vectors[index])
            scored.append((score, index, snippet))
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        return [
            _with_metadata(
                snippet=snippet,
                score=score,
                rank=rank,
                retriever=self.backend_name,
                matched_tags=_matched_tags(query, snippet),
            )
            for rank, (score, _, snippet) in enumerate(ranked[:limit], start=1)
        ]


class KeywordRetriever:
    backend_name = "keyword"

    def __init__(self, snippets: list[KnowledgeSnippet]):
        self._snippets = list(snippets)

    def retrieve(self, query: str, limit: int) -> list[KnowledgeSnippet]:
        scored = [(_keyword_score(query, snippet), index, snippet) for index, snippet in enumerate(self._snippets)]
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        relevant = [(score, snippet) for score, _, snippet in ranked if score > 0]
        if not relevant:
            relevant = [(score, snippet) for score, _, snippet in ranked]
        return [
            _with_metadata(
                snippet=snippet,
                score=float(score),
                rank=rank,
                retriever=self.backend_name,
                matched_tags=_matched_tags(query, snippet),
            )
            for rank, (score, snippet) in enumerate(relevant[:limit], start=1)
        ]


class FaissRetriever:
    backend_name = "faiss"

    def __init__(self, snippets: list[KnowledgeSnippet]):
        try:
            import faiss  # noqa: F401
        except ImportError as exc:
            raise OptionalDependencyError(
                "FAISS backend requires optional dependency: pip install 'uav-mission-intelligence-agent[rag-faiss]'"
            ) from exc
        self._delegate = LocalVectorRetriever(snippets)

    def retrieve(self, query: str, limit: int) -> list[KnowledgeSnippet]:
        return [
            replace(snippet, retriever=self.backend_name)
            for snippet in self._delegate.retrieve(query, limit)
        ]


class ChromaRetriever:
    backend_name = "chroma"

    def __init__(self, snippets: list[KnowledgeSnippet]):
        try:
            import chromadb  # noqa: F401
        except ImportError as exc:
            raise OptionalDependencyError(
                "Chroma backend requires optional dependency: pip install 'uav-mission-intelligence-agent[rag-chroma]'"
            ) from exc
        self._delegate = LocalVectorRetriever(snippets)

    def retrieve(self, query: str, limit: int) -> list[KnowledgeSnippet]:
        return [
            replace(snippet, retriever=self.backend_name)
            for snippet in self._delegate.retrieve(query, limit)
        ]


def _with_metadata(
    *,
    snippet: KnowledgeSnippet,
    score: float,
    rank: int,
    retriever: str,
    matched_tags: list[str],
) -> KnowledgeSnippet:
    return replace(
        snippet,
        score=round(score, 6),
        rank=rank,
        retriever=retriever,
        matched_tags=matched_tags,
    )


def _snippet_text(snippet: KnowledgeSnippet) -> str:
    return " ".join([snippet.topic, snippet.content, *snippet.tags])


def _matched_tags(query: str, snippet: KnowledgeSnippet) -> list[str]:
    normalized = query.lower()
    return [tag for tag in snippet.tags if tag.lower() in normalized]


def _keyword_score(query: str, snippet: KnowledgeSnippet) -> int:
    terms = [term for term in re.split(r"[\s,，。；;]+", query) if term]
    score = 0
    for tag in snippet.tags:
        if tag in query:
            score += 3
    for term in terms:
        if term in snippet.content or term in snippet.topic:
            score += 1
    return score
```

- [ ] **Step 4: Run retriever tests to verify they pass**

Run: `python -B -m unittest tests.test_knowledge_retrieval -v`

Expected: PASS.

### Task 3: Integrate KnowledgeBase Facade

**Files:**
- Modify: `src/uav_mission_agent/knowledge_base.py`
- Modify: `tests/test_workflow.py`
- Modify: `tests/test_knowledge_retrieval.py`

**Interfaces:**
- Consumes: `build_retriever(backend: str, snippets: list[KnowledgeSnippet]) -> Retriever`
- Produces: `KnowledgeBase.default(retriever_backend: str = "local-vector") -> KnowledgeBase`
- Produces: `KnowledgeBase.from_snippets(snippets: list[KnowledgeSnippet], retriever_backend: str = "local-vector") -> KnowledgeBase`

- [ ] **Step 1: Add failing KnowledgeBase integration tests**

Append to `tests/test_knowledge_retrieval.py`:

```python
from uav_mission_agent.knowledge_base import KnowledgeBase


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
```

Modify `tests/test_workflow.py` in `test_workflow_returns_structured_plan_and_config` after retrieved knowledge assertion:

```python
        self.assertEqual(result["retrieved_knowledge"][0]["retriever"], "local-vector")
        self.assertIn("score", result["retrieved_knowledge"][0])
        self.assertIn("rank", result["retrieved_knowledge"][0])
```

- [ ] **Step 2: Run integration tests to verify they fail**

Run: `python -B -m unittest tests.test_knowledge_retrieval tests.test_workflow -v`

Expected: FAIL because `KnowledgeBase.from_snippets` does not exist and workflow snippets lack retrieval metadata.

- [ ] **Step 3: Refactor `knowledge_base.py` to delegate to retrievers**

Modify `src/uav_mission_agent/knowledge_base.py`:

```python
from __future__ import annotations

from .models import KnowledgeSnippet
from .retrievers import Retriever, build_retriever


class KnowledgeBase:
    def __init__(self, snippets: list[KnowledgeSnippet], retriever_backend: str = "local-vector"):
        self._snippets = list(snippets)
        self._retriever: Retriever = build_retriever(retriever_backend, self._snippets)

    @classmethod
    def default(cls, retriever_backend: str = "local-vector") -> "KnowledgeBase":
        return cls(_default_snippets(), retriever_backend=retriever_backend)

    @classmethod
    def from_snippets(
        cls,
        snippets: list[KnowledgeSnippet],
        retriever_backend: str = "local-vector",
    ) -> "KnowledgeBase":
        return cls(snippets, retriever_backend=retriever_backend)

    def retrieve(self, query: str, limit: int = 3) -> list[KnowledgeSnippet]:
        return self._retriever.retrieve(query, limit)


def _default_snippets() -> list[KnowledgeSnippet]:
    return [
        KnowledgeSnippet(
            topic="coverage_search",
            content="多无人机搜索任务通常先进行区域分解，再按照覆盖率、航程约束和目标优先级分配航迹。",
            tags=["多无人机", "搜索", "覆盖", "区域", "area_search"],
        ),
        KnowledgeSnippet(
            topic="low_bandwidth_coordination",
            content="弱通信条件下应减少全局同步依赖，优先采用局部感知、事件触发通信和分布式协同策略。",
            tags=["弱通信", "通信", "低通量", "协同", "distributed"],
        ),
        KnowledgeSnippet(
            topic="no_fly_zone_avoidance",
            content="存在禁飞区时，任务配置应显式保留避让区域，并在航迹规划阶段加入硬约束或高惩罚代价。",
            tags=["禁飞区", "避开", "约束", "航迹规划", "avoid"],
        ),
        KnowledgeSnippet(
            topic="risk_management",
            content="无人机任务风险主要来自通信中断、覆盖不足、机间冲突、目标丢失和能量约束。",
            tags=["风险", "通信", "覆盖不足", "冲突", "能量"],
        ),
        KnowledgeSnippet(
            topic="dynamic_replanning",
            content="动态禁飞区或突发障碍出现时，需要触发局部重规划，并检查绕飞后的航程、覆盖率和安全间隔。",
            tags=["重新规划", "重规划", "动态", "禁飞区", "避障"],
        ),
        KnowledgeSnippet(
            topic="target_tracking",
            content="多无人机目标跟踪任务应保持目标持续观测，并通过分布式协同降低遮挡、丢失和重复跟踪风险。",
            tags=["跟踪", "追踪", "目标", "多无人机", "协同"],
        ),
    ]
```

- [ ] **Step 4: Run integration tests to verify they pass**

Run: `python -B -m unittest tests.test_knowledge_retrieval tests.test_workflow -v`

Expected: PASS.

### Task 4: Packaging And Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/engineering.md`
- Modify: `tests/test_readme_assets.py`

**Interfaces:**
- Consumes: `KnowledgeBase.default(retriever_backend="local-vector")`
- Produces: optional extras `rag-faiss`, `rag-chroma`, and `rag`

- [ ] **Step 1: Add failing packaging/documentation tests**

Append to `tests/test_readme_assets.py`:

```python
    def test_readme_documents_vector_rag_backends(self):
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertIn("local vector RAG", readme)
        self.assertIn("rag-faiss", readme)
        self.assertIn("rag-chroma", readme)
        self.assertNotIn("RAG-ready; the local knowledge retriever can later be replaced", readme)
```

Create or append to `tests/test_knowledge_retrieval.py`:

```python
class PackagingConfigTests(unittest.TestCase):
    def test_pyproject_declares_optional_rag_extras(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('rag-faiss = ["faiss-cpu>=1.8"]', pyproject)
        self.assertIn('rag-chroma = ["chromadb>=0.5"]', pyproject)
        self.assertIn('"faiss-cpu>=1.8"', pyproject)
        self.assertIn('"chromadb>=0.5"', pyproject)
```

- [ ] **Step 2: Run documentation tests to verify they fail**

Run: `python -B -m unittest tests.test_readme_assets tests.test_knowledge_retrieval.PackagingConfigTests -v`

Expected: FAIL because README and `pyproject.toml` are not updated.

- [ ] **Step 3: Update optional dependencies**

Modify `pyproject.toml`:

```toml
[project.optional-dependencies]
langgraph = ["langgraph>=0.2"]
rag-faiss = ["faiss-cpu>=1.8"]
rag-chroma = ["chromadb>=0.5"]
rag = [
    "faiss-cpu>=1.8",
    "chromadb>=0.5",
]
```

- [ ] **Step 4: Update README and engineering docs**

Update README:

- Replace module table row for `knowledge_base.py` with local vector RAG wording.
- Replace "RAG-ready" evidence bullet with implemented local vector RAG wording.
- Remove the roadmap bullet saying FAISS/Chroma replacement is future work.
- Add a short "RAG Retrieval Backends" section showing:

```powershell
pip install "uav-mission-intelligence-agent[rag-faiss]"
pip install "uav-mission-intelligence-agent[rag-chroma]"
```

Add a retrieval evidence example:

```json
{
  "topic": "low_bandwidth_coordination",
  "retriever": "local-vector",
  "rank": 1,
  "score": 0.42,
  "matched_tags": ["distributed"]
}
```

Update `docs/engineering.md` with the same backend names and the default offline behavior.

- [ ] **Step 5: Run documentation tests to verify they pass**

Run: `python -B -m unittest tests.test_readme_assets tests.test_knowledge_retrieval.PackagingConfigTests -v`

Expected: PASS.

### Task 5: Final Verification And Commit

**Files:**
- All modified files from Tasks 1-4

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: committed local vector RAG upgrade.

- [ ] **Step 1: Run focused retrieval tests**

Run: `python -B -m unittest tests.test_embeddings tests.test_knowledge_retrieval tests.test_workflow -v`

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run: `python -B -m unittest discover -s tests -v`

Expected: PASS with all tests OK.

- [ ] **Step 3: Run consistency checks**

Run: `rg -n "RAG-ready|later be replaced by FAISS|Replace the local retriever with FAISS or Chroma" README.md docs`

Expected: no matches.

Run: `git diff --check`

Expected: exit 0. Windows LF/CRLF warnings are acceptable; whitespace errors are not.

- [ ] **Step 4: Review diff scope**

Run: `git status -sb`

Expected: only RAG implementation, docs, and plan/spec files are modified.

- [ ] **Step 5: Commit**

Run:

```powershell
git add README.md docs\engineering.md docs\superpowers\plans\2026-07-09-rag-vector-retrieval.md pyproject.toml src\uav_mission_agent\embeddings.py src\uav_mission_agent\knowledge_base.py src\uav_mission_agent\models.py src\uav_mission_agent\retrievers.py tests\test_embeddings.py tests\test_knowledge_retrieval.py tests\test_readme_assets.py tests\test_workflow.py
git commit -m "feat: add local vector RAG retrieval"
```

Expected: commit created.
