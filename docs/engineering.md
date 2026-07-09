# Engineering Notes

## Architecture

The project keeps the default execution path offline and reproducible while preserving hooks for real LLM providers.

```text
mission text
  -> task_parser_agent
  -> knowledge_retriever_agent
  -> mission_planner_agent
       -> optional DeepSeek / OpenAI-compatible refinement
  -> mission_reviewer_agent
  -> schema validation
  -> benchmark / dashboard
```

Key modules:

| Module | Purpose |
|---|---|
| `agent_graph.py` | Traceable parser, retriever, planner, and reviewer nodes. |
| `workflow.py` | End-to-end mission workflow with rule-based or optional LangGraph backend. |
| `embeddings.py` | Deterministic local sparse-vector embeddings and cosine similarity. |
| `retrievers.py` | Retrieval backend implementations for `local-vector`, `keyword`, optional `faiss`, and optional `chroma`. |
| `knowledge_base.py` | Stable knowledge-base facade using local vector RAG by default. |
| `llm_provider.py` | OpenAI-compatible provider adapter, including the DeepSeek alias. |
| `costing.py` | Token usage normalization and configurable cost estimation. |
| `benchmark.py` | Stable v1 benchmark summary. |
| `benchmark_v2.py` | Provider comparison, latency, token usage, cost, and difficulty summaries. |
| `dashboard.py` | Static local HTML dashboard with Agent flow and Benchmark v2 sections. |

## RAG Retrieval

The default retrieval backend is `local-vector`. It runs offline with deterministic sparse-vector embeddings, cosine similarity, and tag-match boosting. Retrieved snippets include:

- `retriever`: backend name, such as `local-vector`
- `rank`: 1-based retrieval rank
- `score`: retrieval score after vector similarity and tag evidence
- `matched_tags`: snippet tags that appeared in the query

The stable agent-facing API is:

```python
KnowledgeBase.default().retrieve("weak communication UAV search", limit=3)
```

Optional adapter boundaries are available for standard vector-store stacks:

```powershell
python -m pip install -e ".[rag-faiss]"
python -m pip install -e ".[rag-chroma]"
```

If those packages are not installed, selecting `faiss` or `chroma` raises a clear optional-dependency error with the matching install hint. Unit tests do not require FAISS, Chroma, API keys, or network access.

## Benchmark v2

Run the offline baseline:

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --benchmark-v2 data\scenarios
```

Compare multiple providers:

```powershell
$env:PYTHONPATH="src"
$env:DEEPSEEK_API_KEY="your-api-key"
python -m uav_mission_agent.cli --benchmark-v2 data\scenarios --benchmark-providers offline,deepseek
```

Use `provider/model` when a specific model should be compared:

```powershell
$env:PYTHONPATH="src"
$env:DEEPSEEK_API_KEY="your-api-key"
python -m uav_mission_agent.cli --benchmark-v2 data\scenarios --benchmark-providers offline,deepseek/deepseek-v4-flash
```

Benchmark v2 returns:

- `summary`: benchmark version, scenario count, provider count, total runs, average score, pass count, latency, and estimated total cost.
- `provider_comparison`: provider-level average score, pass count, latency, and estimated cost.
- `difficulty_summary`: grouped score by scenario difficulty.
- `results`: per-provider, per-scenario records with score breakdown, schema validity, token usage, and estimated cost.

## Real Provider Calls

The default benchmark and dashboard do not call external APIs. Real calls are made only when a live provider is requested.

DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY="your-api-key"
python -m uav_mission_agent.cli --llm-provider deepseek "use 3 UAVs to search area A and avoid no-fly zone B"
```

OpenAI-compatible:

```powershell
$env:OPENAI_API_KEY="your-api-key"
python -m uav_mission_agent.cli --llm-provider openai-compatible --llm-model gpt-4o-mini --llm-base-url https://api.openai.com/v1 "use 3 UAVs to search area A"
```

The provider adapter stores returned `usage` metadata as `llm_metadata.usage` when the API response includes token usage fields.

## Cost Estimation

Cost is estimated from:

```text
input_cost = prompt_tokens / 1,000,000 * input_per_1m_tokens
output_cost = completion_tokens / 1,000,000 * output_per_1m_tokens
```

Provider prices change over time, so the project treats pricing as explicit run configuration. Use the provider's current pricing page before publishing live cost numbers:

- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
- OpenAI pricing: https://platform.openai.com/docs/pricing

Pass pricing from the CLI:

```powershell
$env:PYTHONPATH="src"
$env:DEEPSEEK_API_KEY="your-api-key"
python -m uav_mission_agent.cli `
  --benchmark-v2 data\scenarios `
  --benchmark-providers offline,deepseek/deepseek-v4-flash `
  --benchmark-pricing deepseek/deepseek-v4-flash:0.14:0.28:USD
```

Update the pricing values to the provider's current input and output prices per 1M tokens before using the cost report externally.

## Dashboard

Generate the local HTML dashboard:

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --dashboard dashboard\uav_mission_dashboard.html
```

The dashboard shows:

- mission input
- Agent node flow
- planning recommendations and risks
- structured mission config
- Benchmark v2 score cards
- provider comparison
- token and estimated cost summary
- raw Agent JSON and Benchmark v2 JSON

## Testing and CI

Run the full unit test suite:

```bash
python -B -m unittest discover -s tests -v
```

The GitHub Actions workflow runs the same test suite on every push and pull request. Tests use offline or fake providers only, so CI does not require API keys.

## API Key Hygiene

- Store keys in environment variables only.
- Do not put keys in README files, examples, tests, screenshots, or commits.
- Prefer fake providers in tests.
- If a key is ever pasted into a public place, revoke it immediately and create a new one.
