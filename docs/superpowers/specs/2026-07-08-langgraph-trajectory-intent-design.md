# LangGraph Trajectory Intent Design

## Goal

Add a LangGraph-backed mission workflow and a small UAV trajectory / intent recognition module while preserving the existing offline workflow and the real DeepSeek / OpenAI-compatible provider interface.

## Current Context

The project is a dependency-light Python package. The current mission workflow is implemented in `agent_graph.py`, exposed through `workflow.py`, and called from `cli.py`. It already supports an optional `LLMProvider` interface with DeepSeek and OpenAI-compatible providers. Local `langgraph` is not installed, so the LangGraph path must be optional and must fail with a clear error when requested without the dependency.

## Requirements

- Keep the existing rule-based workflow as the default path.
- Add a real LangGraph backend that uses `StateGraph`, `START`, `END`, `compile()`, and `invoke()` when `langgraph` is installed.
- Do not break or replace the existing DeepSeek / OpenAI-compatible provider adapter.
- Add CLI selection for mission graph backend: `--graph-backend rule-based|langgraph`.
- Add a small UAV trajectory module that accepts structured points with latitude, longitude, altitude, timestamp, speed, heading, roll, pitch, and yaw.
- Add trajectory summary features: point count, duration, altitude trend, speed trend, heading change, mean speed, and mean altitude.
- Add an intent recognition module that maps trajectory summaries to `area_search`, `target_tracking`, `return_to_base`, `loitering`, or `transit`.
- Add a CLI mode for trajectory intent recognition from a JSON file.
- Keep all new functionality testable without network calls and without requiring a real DeepSeek API key.
- Document LangGraph usage, optional dependency installation, trajectory input format, and CLI examples in `README.md`.

## Architecture

### Mission Graph Backends

`agent_graph.py` remains the default dependency-free workflow. New module `langgraph_workflow.py` builds a LangGraph graph using the same task parsing, retrieval, planning, and review semantics. The LangGraph module exposes:

- `LangGraphUnavailableError`
- `run_langgraph_workflow(text, knowledge_base=None, llm_provider=None)`
- `build_langgraph_app(graph_api=None)`

`graph_api` exists only to make the official LangGraph API path testable without installing the external dependency. Production calls do not pass it; the module imports `langgraph.graph` directly.

### Workflow Selection

`workflow.py` exposes a `graph_backend` argument. `rule-based` calls the current implementation. `langgraph` calls `run_langgraph_workflow`. `cli.py` exposes the same choice through `--graph-backend`.

### Trajectory Intent Modules

`trajectory.py` owns trajectory parsing and numerical summary. It defines dataclasses:

- `TrajectoryPoint`
- `TrajectorySummary`

`intent_recognition.py` owns rule-based intent recognition. It defines:

- `IntentRecognitionResult`
- `recognize_intent(points)`

The first version is intentionally deterministic and lightweight. It is a public prototype that makes the UAV trajectory / intent recognition direction visible in the project. A later version can replace this with a BiLSTM or Transformer classifier while keeping the same input and output contract.

### CLI

`cli.py` gains:

- `--graph-backend rule-based|langgraph` for mission planning.
- `--trajectory-intent PATH` for recognizing intent from a JSON list of trajectory points.

Mission mode keeps the current provider flags. This preserves real AI access through DeepSeek / OpenAI-compatible providers:

- `--llm-provider deepseek`
- `--llm-provider openai-compatible`
- `--llm-model`
- `--llm-base-url`
- `--llm-api-key-env`

### Error Handling

If `--graph-backend langgraph` is used without `langgraph` installed, the CLI returns a parser error telling the user to install the optional dependency. If trajectory JSON is malformed, the parser raises a clear `ValueError` describing the invalid point or missing field.

## Testing

Tests use TDD and avoid network calls:

- LangGraph backend test uses a fake `StateGraph` API and verifies node order, compile, invoke, and output structure.
- CLI test verifies `--graph-backend langgraph` reports a clear missing dependency error when `langgraph` is not installed.
- Trajectory tests verify summary trends and intent labels.
- CLI trajectory test verifies JSON file input and structured JSON output.
- Full regression tests must still pass.

## Documentation

README updates include:

- Optional LangGraph installation and CLI usage.
- Explanation that rule-based remains default.
- Trajectory JSON example.
- Intent recognition CLI example.
- Note that DeepSeek and OpenAI-compatible provider interfaces are preserved.

## Non-Goals

- Do not implement BiLSTM training in this step.
- Do not require LangGraph for default usage.
- Do not call DeepSeek during tests.
- Do not add a database or vector store dependency in this step.
