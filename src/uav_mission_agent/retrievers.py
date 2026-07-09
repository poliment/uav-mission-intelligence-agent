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
            matched_tags = _matched_tags(query, snippet)
            score = cosine_similarity(query_vector, self._vectors[index]) + (0.1 * len(matched_tags))
            scored.append((score, index, snippet, matched_tags))
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        return [
            _with_metadata(
                snippet=snippet,
                score=score,
                rank=rank,
                retriever=self.backend_name,
                matched_tags=matched_tags,
            )
            for rank, (score, _, snippet, matched_tags) in enumerate(ranked[:limit], start=1)
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
        return [replace(snippet, retriever=self.backend_name) for snippet in self._delegate.retrieve(query, limit)]


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
        return [replace(snippet, retriever=self.backend_name) for snippet in self._delegate.retrieve(query, limit)]


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
