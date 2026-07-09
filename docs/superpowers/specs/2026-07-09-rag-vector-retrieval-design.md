# RAG Vector Retrieval Upgrade Design

## Objective

Upgrade the UAV Mission Intelligence Agent from a keyword-style local retriever into a standard RAG-oriented retrieval layer while preserving the default offline, dependency-light workflow.

## Scope

- Keep `KnowledgeBase.retrieve(query, limit=3)` as the stable public retrieval API for the agent workflow.
- Add a deterministic local vector retriever that works without network access, API keys, or third-party packages.
- Add optional FAISS and Chroma adapter boundaries so the project can advertise and support standard vector-store integration without making those packages required for default use.
- Add retrieval metadata for project evidence: backend name, similarity score, rank, and matched tags.
- Keep benchmark, dashboard, LangGraph, and live provider paths working through the existing `KnowledgeBase` contract.
- Update README and engineering docs so the project moves from "RAG-ready" to "local vector RAG with optional FAISS/Chroma backends."

## Non-Goals

- Do not require FAISS, Chroma, sentence-transformers, OpenAI embeddings, or any network embedding API for default execution.
- Do not add persistent vector database files in this step.
- Do not change the mission planner, task parser, benchmark scoring, or LLM provider adapter behavior except where they consume richer retrieval metadata.
- Do not make unit tests depend on installed FAISS or Chroma packages.
- Do not call external services during tests.

## Architecture

The retrieval layer will be split into three small units:

- `embeddings.py`: deterministic text embedding utilities used by the default offline backend.
- `retrievers.py`: retriever protocols and backend implementations.
- `knowledge_base.py`: source snippets plus the stable `KnowledgeBase` facade used by the agent workflow.

The default backend is `local-vector`. It converts snippet text and query text into deterministic sparse vectors using token and character n-gram features, then ranks snippets by cosine similarity. This is not a production embedding model, but it gives the repository a real vector retrieval pipeline that is explainable, deterministic, and CI-friendly.

Optional backends are exposed as adapters:

- `faiss`: imports `faiss` only when selected; if unavailable, raises a clear `OptionalDependencyError`.
- `chroma`: imports `chromadb` only when selected; if unavailable, raises a clear `OptionalDependencyError`.

The adapters share the same interface as the local backend, so later work can replace the deterministic embedding with model-based embeddings without changing the agent graph.

## Data Model Changes

`KnowledgeSnippet` will be extended with optional retrieval fields:

- `score: float | None`
- `rank: int | None`
- `retriever: str | None`
- `matched_tags: list[str]`

These fields are optional so existing snippets and tests remain easy to construct. `to_dict()` will include them so agent output, dashboard JSON, and live LLM provider context show retrieval evidence.

## Backend Selection

`KnowledgeBase.default()` will use `local-vector`.

Additional construction helpers:

- `KnowledgeBase.default(retriever_backend="local-vector")`
- `KnowledgeBase.from_snippets(snippets, retriever_backend="local-vector")`

Supported backend names:

- `local-vector`
- `keyword`
- `faiss`
- `chroma`

The `keyword` backend remains available as a fallback and regression comparison path, but README should present `local-vector` as the default RAG backend.

## Retrieval Flow

1. `run_agent_workflow()` creates `KnowledgeBase.default()` unless one is injected.
2. `_knowledge_retriever_agent()` calls `knowledge_base.retrieve(raw_request, limit=3)`.
3. `KnowledgeBase` delegates to the configured retriever backend.
4. The backend returns cloned `KnowledgeSnippet` objects with retrieval metadata attached.
5. Planner and LLM provider paths continue to consume the returned snippets through `snippet.to_dict()`.

## Error Handling

- Unknown backend names raise `ValueError("unsupported retriever backend: <name>")`.
- Selecting `faiss` without FAISS installed raises `OptionalDependencyError` with an install hint: `pip install 'uav-mission-intelligence-agent[rag-faiss]'`.
- Selecting `chroma` without Chroma installed raises `OptionalDependencyError` with an install hint: `pip install 'uav-mission-intelligence-agent[rag-chroma]'`.
- Empty queries still return the top snippets by deterministic fallback order, preserving current behavior.

## Packaging

`pyproject.toml` will add optional dependencies:

```toml
[project.optional-dependencies]
rag-faiss = ["faiss-cpu>=1.8"]
rag-chroma = ["chromadb>=0.5"]
rag = [
  "faiss-cpu>=1.8",
  "chromadb>=0.5",
]
```

The existing `langgraph` extra remains unchanged.

## Testing Strategy

Unit tests will cover:

- Local vector retrieval ranks mission-relevant snippets above unrelated snippets.
- Retrieval output includes score, rank, retriever, and matched tags.
- `KnowledgeBase.retrieve()` preserves the existing API and returns `KnowledgeSnippet` objects.
- Unknown backend names fail clearly.
- FAISS and Chroma adapters fail clearly when optional dependencies are missing.
- The end-to-end workflow still returns retrieved knowledge and passes schema validation.
- The full suite remains offline and does not require FAISS, Chroma, API keys, or network access.

## Documentation Updates

README will be updated to:

- Describe the project as using local vector RAG by default.
- Replace "RAG-ready" wording with implemented retrieval capabilities.
- Show optional install commands for FAISS and Chroma extras.
- Show a small retrieval evidence example with backend, score, and rank.
- Keep the warning that the default workflow remains offline and dependency-light.

`docs/engineering.md` will be updated with the retrieval architecture and backend selection notes.

## Acceptance Criteria

- `python -B -m unittest discover -s tests -v` passes.
- Default mission workflow runs without third-party dependencies or API keys.
- `KnowledgeBase.default().retrieve("multi UAV weak communication search", limit=3)` returns snippets with vector retrieval metadata.
- Optional FAISS/Chroma selection produces clear install guidance when the packages are not installed.
- README no longer says FAISS/Chroma replacement is only future work.
- Public project positioning remains technical and project-oriented, not job-search-oriented.
