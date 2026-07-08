# Benchmark v2, Provider Comparison, and Dashboard v2 Design

## Objective

Extend the UAV Mission Intelligence Agent from a single offline benchmark into a reproducible evaluation surface that can compare offline, DeepSeek, and OpenAI-compatible providers while reporting quality, latency, token usage, and estimated cost.

## Scope

- Keep the default path fully offline and testable without API keys.
- Add Benchmark v2 with provider-level and scenario-level metrics.
- Support real LLM execution through the existing provider adapter when API keys are present.
- Add cost estimation from provider usage metadata and configurable per-token pricing.
- Upgrade the local HTML dashboard so it shows provider comparison, Benchmark v2 metrics, and cost statistics.
- Add engineering documentation for architecture, API keys, benchmark extension, and CI/test commands.

## Non-Goals

- Do not commit API keys, model secrets, or live provider outputs that depend on private credentials.
- Do not require network access for unit tests or the default dashboard.
- Do not replace the existing v1 benchmark CLI path; keep it as a stable simple report.
- Do not add heavyweight dashboard dependencies unless the static HTML path cannot satisfy the request.

## Functional Requirements

### Benchmark v2

- Accept a list of UAV mission scenarios.
- Run each scenario against one or more provider configurations.
- Record per-run metadata:
  - scenario id, name, difficulty
  - provider label, provider type, model, graph backend
  - score, breakdown, missing requirements
  - schema validation status
  - latency in milliseconds
  - token usage if the provider exposes usage metadata
  - estimated cost if pricing is configured
- Produce aggregate metrics:
  - scenario count, provider count, run count
  - average score and passed run count
  - average latency
  - estimated total cost
  - grouped summaries by provider and difficulty

### Provider Comparison

- Support an offline baseline provider that uses the current rule-based workflow and has zero LLM token cost.
- Support live providers through `build_llm_provider`, especially:
  - `deepseek`
  - `openai-compatible`
- Allow CLI provider lists such as `offline,deepseek`.
- If a live provider is requested without a key, return a clear CLI error that names the missing environment variable.
- Unit tests must use fake/injected providers only.

### Cost Statistics

- Capture token usage from OpenAI-compatible API responses when the API returns a `usage` object.
- Estimate cost from prompt/input tokens and completion/output tokens.
- Treat pricing as provider/model configuration rather than a permanent truth.
- Include official pricing references in docs:
  - DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
  - OpenAI/API provider pricing should be verified from that provider's current pricing page before a live report is used externally.

### Dashboard v2

- Keep the dashboard as a local static HTML file.
- Display:
  - mission input
  - agent node flow
  - planning recommendations
  - risk explanation
  - mission config
  - Benchmark v2 score summary
  - provider comparison table
  - cost summary
  - raw Agent JSON and Benchmark v2 JSON
- Use offline Benchmark v2 by default so dashboard generation works without credentials.

### Engineering Documentation

- Document the main modules and data flow.
- Document local test commands and CI expectations.
- Document how to run offline Benchmark v2.
- Document how to run live DeepSeek/OpenAI-compatible comparisons with environment variables.
- Document cost-estimation caveats and provider pricing verification.

## Acceptance Criteria

- `python -m unittest discover -s tests -v` passes.
- Benchmark v2 can run offline over `data/scenarios`.
- CLI can print Benchmark v2 JSON.
- Dashboard generation succeeds without API keys and includes provider/cost sections.
- Real provider support remains available through environment variables, without any secrets committed.
- README and engineering docs explain the new commands and API-key requirements.
