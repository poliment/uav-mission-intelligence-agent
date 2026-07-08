# Implementation Plan: Benchmark v2 and Dashboard v2

## Phase 1: Costing Foundation

- Add focused tests for token usage normalization and cost estimation.
- Implement a small `costing.py` module with:
  - token usage normalization
  - provider pricing data
  - per-run and aggregate cost estimation
- Extend the OpenAI-compatible provider to retain response usage metadata after a call.

## Phase 2: Benchmark v2

- Add tests for an offline Benchmark v2 run.
- Add tests for a fake live provider that exposes token usage.
- Implement `benchmark_v2.py` with:
  - provider configuration dataclass
  - offline baseline
  - provider factory hook for real DeepSeek/OpenAI-compatible calls
  - per-scenario run records
  - provider and difficulty aggregates
- Keep the existing v1 `benchmark.py` behavior unchanged.

## Phase 3: CLI Integration

- Add tests for `--benchmark-v2`.
- Add CLI flags:
  - `--benchmark-v2 SCENARIO_DIR`
  - `--benchmark-providers offline,deepseek,openai-compatible`
  - `--benchmark-pricing MODEL:INPUT_PER_1M:OUTPUT_PER_1M`
- Return a clear parser error if a requested live provider has no API key.

## Phase 4: Dashboard v2

- Update dashboard tests for Benchmark v2 sections.
- Render:
  - summary metrics
  - provider comparison table
  - estimated cost table
  - per-scenario score cards
- Regenerate `dashboard/uav_mission_dashboard.html`.

## Phase 5: Engineering Docs and Verification

- Add `docs/engineering.md`.
- Update README with Benchmark v2, live-provider, dashboard, and cost-stat sections.
- Regenerate representative result JSON if needed.
- Run:
  - full unit tests
  - CLI smoke tests
  - dashboard smoke test
  - syntax checks
  - secret scan
- Commit and push to `origin/main`.
