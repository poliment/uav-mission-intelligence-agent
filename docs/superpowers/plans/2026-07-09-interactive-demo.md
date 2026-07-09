# Interactive FastAPI Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI + HTML demo where a user can enter a UAV mission, select a provider, and inspect Agent trace, JSON output, benchmark/provider comparison, and the mission situation map.

**Architecture:** Add a dependency-free `demo_service.py` that owns payload construction, benchmark loading, error normalization, and HTML rendering. Add optional FastAPI route wiring in `demo_app.py`, plus a small `demo_cli.py` launcher that can load the existing DeepSeek `.env` file without printing secrets.

**Tech Stack:** Python standard library, existing UAV Agent modules, optional `fastapi>=0.100`, optional `uvicorn>=0.23`, existing `unittest` suite, plain HTML/CSS/JavaScript.

## Global Constraints

- Keep FastAPI and Uvicorn as optional demo dependencies only.
- Do not require FastAPI, Uvicorn, API keys, network access, or live provider calls for the default unit test suite.
- Do not expose API key values in UI, logs, JSON responses, tests, screenshots, or commits.
- Do not replace the existing Agent workflow, local vector RAG, Benchmark v2, static dashboard, or provider adapter.
- Prefer the saved 31-scenario report at `results/deepseek_provider_comparison_2026-07-09.json`; fall back to offline Benchmark v2 when it is absent or invalid.
- The first screen must be the working demo, not a landing page.

---

## File Structure

- Create `src/uav_mission_agent/demo_service.py`: dependency-free service functions for demo mission payloads, benchmark report loading, safe errors, env-file loading, and HTML rendering.
- Create `src/uav_mission_agent/demo_app.py`: optional FastAPI app factory and route handlers.
- Create `src/uav_mission_agent/demo_cli.py`: command-line parser, env-file loading, and Uvicorn launcher.
- Modify `pyproject.toml`: add `demo` extra and `uav-mission-agent-demo` script.
- Modify `README.md`: add interactive demo install/run docs and update module/project positioning.
- Modify `docs/engineering.md`: document demo service/UI boundary.
- Create `tests/test_demo_service.py`: default-suite tests for service behavior with no FastAPI dependency.
- Create `tests/test_demo_cli.py`: default-suite tests for env loading and launcher argument parsing without starting a server.
- Create `tests/test_demo_app.py`: FastAPI route tests skipped when FastAPI is unavailable.

---

### Task 1: Dependency-Free Demo Service

**Files:**
- Create: `src/uav_mission_agent/demo_service.py`
- Create: `tests/test_demo_service.py`

**Interfaces:**
- Consumes:
  - `run_agent_workflow(text: str, knowledge_base=None, llm_provider=None) -> dict`
  - `build_llm_provider(provider_name: str | None, *, api_key=None, api_key_env=None, model=None, base_url=None) -> LLMProvider | None`
  - `render_mission_execution_svg(plan: dict[str, Any]) -> str`
  - `run_benchmark_v2(scenarios: Iterable[MissionScenario]) -> dict` for default offline benchmark usage
  - `load_scenarios(path: str | Path) -> list[MissionScenario]`
- Produces:
  - `class DemoError(RuntimeError)`
  - `build_mission_demo_payload(mission_text: str, provider: str = "offline", model: str | None = None, base_url: str | None = None, provider_factory=build_llm_provider, workflow_runner=run_agent_workflow) -> dict[str, Any]`
  - `load_demo_benchmark(report_path: str | Path | None = DEFAULT_BENCHMARK_REPORT, scenario_dir: str | Path = DEFAULT_SCENARIO_DIR, benchmark_runner=run_benchmark_v2, scenario_loader=load_scenarios) -> dict[str, Any]`
  - `load_env_file(path: str | Path) -> dict[str, str]`
  - `build_demo_html() -> str`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_demo_service.py`:

```python
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.demo_service import (
    DemoError,
    build_demo_html,
    build_mission_demo_payload,
    load_demo_benchmark,
    load_env_file,
)
from uav_mission_agent.llm_provider import LLMProviderError


class DemoServiceTests(unittest.TestCase):
    def test_offline_mission_payload_contains_trace_json_and_svg(self):
        payload = build_mission_demo_payload(
            "Use 3 UAVs to search area A, avoid no-fly zone B, and maintain weak communication coordination."
        )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["provider"]["name"], "offline")
        self.assertFalse(payload["provider"]["live"])
        self.assertEqual(payload["plan"]["agent_trace"][0]["node"], "task_parser_agent")
        self.assertIn("mission_planner_agent", [step["node"] for step in payload["agent_trace"]])
        self.assertTrue(payload["schema_validation"]["valid"])
        self.assertIn('"mission_config"', payload["json_plan"])
        self.assertIn("<svg", payload["mission_svg"])
        self.assertIn("Mission Execution Visualization", payload["mission_svg"])

    def test_empty_mission_text_fails_with_validation_error(self):
        with self.assertRaises(DemoError) as raised:
            build_mission_demo_payload("  ")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.code, "invalid_mission")
        self.assertIn("mission text is required", raised.exception.message)

    def test_unsupported_provider_fails_with_validation_error(self):
        with self.assertRaises(DemoError) as raised:
            build_mission_demo_payload("inspect area A", provider="unknown")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.code, "unsupported_provider")
        self.assertIn("unsupported provider", raised.exception.message)

    def test_provider_factory_error_is_wrapped_without_secret_values(self):
        def failing_factory(*args, **kwargs):
            raise LLMProviderError("missing API key: set DEEPSEEK_API_KEY or pass api_key")

        with self.assertRaises(DemoError) as raised:
            build_mission_demo_payload(
                "inspect area A",
                provider="deepseek",
                provider_factory=failing_factory,
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.code, "provider_error")
        self.assertIn("DEEPSEEK_API_KEY", raised.exception.message)

    def test_load_demo_benchmark_prefers_saved_report(self):
        report = {
            "summary": {"benchmark_version": "2.0", "total_scenarios": 31},
            "provider_comparison": [{"provider_label": "deepseek:deepseek-v4-flash", "average_score": 0.935}],
            "difficulty_summary": [],
            "results": [{"scenario_id": "s001", "score": 0.9}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            payload = load_demo_benchmark(report_path=report_path)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["source"], "saved-report")
        self.assertEqual(payload["summary"]["total_scenarios"], 31)
        self.assertEqual(payload["provider_comparison"][0]["provider_label"], "deepseek:deepseek-v4-flash")
        self.assertIn('"provider_comparison"', payload["json_report"])

    def test_load_demo_benchmark_falls_back_when_report_is_invalid(self):
        fallback_report = {
            "summary": {"benchmark_version": "2.0", "total_scenarios": 1},
            "provider_comparison": [{"provider_label": "offline", "average_score": 0.88}],
            "difficulty_summary": [],
            "results": [{"scenario_id": "fixture", "score": 0.88}],
        }

        def fake_loader(path):
            return ["scenario"]

        def fake_runner(scenarios):
            self.assertEqual(scenarios, ["scenario"])
            return fallback_report

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "broken.json"
            report_path.write_text("{", encoding="utf-8")
            payload = load_demo_benchmark(
                report_path=report_path,
                scenario_dir=Path(tmpdir),
                benchmark_runner=fake_runner,
                scenario_loader=fake_loader,
            )

        self.assertEqual(payload["source"], "offline-fallback")
        self.assertEqual(payload["summary"]["total_scenarios"], 1)
        self.assertEqual(payload["provider_comparison"][0]["provider_label"], "offline")

    def test_load_env_file_sets_values_without_overwriting_existing_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "demo.env"
            env_path.write_text(
                "DEEPSEEK_API_KEY=file-key\n"
                "OPENAI_MODEL='demo-model'\n"
                "# comment line\n"
                "EMPTY_VALUE=\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "existing-key"}, clear=True):
                loaded = load_env_file(env_path)

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "existing-key")
                self.assertEqual(os.environ["OPENAI_MODEL"], "demo-model")
                self.assertEqual(loaded["OPENAI_MODEL"], "demo-model")
                self.assertEqual(loaded["EMPTY_VALUE"], "")

    def test_demo_html_contains_core_interactive_regions(self):
        html = build_demo_html()

        self.assertIn('id="mission-form"', html)
        self.assertIn('id="mission-text"', html)
        self.assertIn('id="provider-select"', html)
        self.assertIn('id="agent-trace"', html)
        self.assertIn('id="json-output"', html)
        self.assertIn('id="benchmark-table"', html)
        self.assertIn('id="mission-map"', html)
        self.assertIn("/api/mission", html)
        self.assertIn("/api/benchmark", html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run service tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_service -v
```

Expected: ERROR with `ModuleNotFoundError: No module named 'uav_mission_agent.demo_service'`.

- [ ] **Step 3: Implement `demo_service.py`**

Create `src/uav_mission_agent/demo_service.py`:

```python
from __future__ import annotations

import html
import json
import os
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .agent_graph import run_agent_workflow
from .benchmark_v2 import run_benchmark_v2
from .dashboard import DEFAULT_SCENARIO_DIR
from .llm_provider import LLMProviderError, build_llm_provider
from .mission_visualization import render_mission_execution_svg
from .scenario_loader import load_scenarios


SUPPORTED_PROVIDERS = {"offline", "deepseek", "openai-compatible"}
DEFAULT_BENCHMARK_REPORT = Path("results") / "deepseek_provider_comparison_2026-07-09.json"
DEMO_DEFAULT_MISSION = (
    "Use 3 UAVs to search area A, avoid no-fly zone B, prioritize suspicious target points, "
    "and maintain coordination under weak communication conditions."
)


class DemoError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


def build_mission_demo_payload(
    mission_text: str,
    provider: str = "offline",
    model: str | None = None,
    base_url: str | None = None,
    provider_factory: Callable = build_llm_provider,
    workflow_runner: Callable = run_agent_workflow,
) -> dict[str, Any]:
    cleaned_mission = mission_text.strip()
    if not cleaned_mission:
        raise DemoError(400, "invalid_mission", "mission text is required")

    provider_name = _normalize_provider(provider)
    llm_provider = _build_demo_provider(
        provider_name=provider_name,
        model=_blank_to_none(model),
        base_url=_blank_to_none(base_url),
        provider_factory=provider_factory,
    )
    try:
        plan = workflow_runner(cleaned_mission, llm_provider=llm_provider)
    except LLMProviderError as exc:
        raise DemoError(400, "provider_error", _safe_message(str(exc))) from exc

    metadata = plan.get("llm_metadata", {})
    provider_model = metadata.get("model") or getattr(llm_provider, "model", None) or (
        "rule-based" if provider_name == "offline" else model
    )
    return {
        "status": "ok",
        "mission_text": cleaned_mission,
        "provider": {
            "name": provider_name,
            "model": provider_model,
            "live": llm_provider is not None,
            "metadata": metadata,
        },
        "plan": plan,
        "json_plan": json.dumps(plan, ensure_ascii=False, indent=2),
        "agent_trace": plan.get("agent_trace", []),
        "agent_review": plan.get("agent_review", {}),
        "schema_validation": plan.get("schema_validation", {}),
        "mission_svg": render_mission_execution_svg(plan),
    }


def load_demo_benchmark(
    report_path: str | Path | None = DEFAULT_BENCHMARK_REPORT,
    scenario_dir: str | Path = DEFAULT_SCENARIO_DIR,
    benchmark_runner: Callable = run_benchmark_v2,
    scenario_loader: Callable[[str | Path], Any] = load_scenarios,
) -> dict[str, Any]:
    if report_path is not None:
        try:
            path = Path(report_path)
            if path.exists():
                report = json.loads(path.read_text(encoding="utf-8"))
                return _normalize_benchmark_report(report, source="saved-report")
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    scenarios = scenario_loader(scenario_dir)
    report = benchmark_runner(scenarios)
    return _normalize_benchmark_report(report, source="offline-fallback")


def load_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_env_quotes(value.strip())
        if key:
            loaded[key] = value
            os.environ.setdefault(key, value)
    return loaded


def build_demo_html() -> str:
    escaped_default = html.escape(DEMO_DEFAULT_MISSION)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UAV Mission Intelligence Demo</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #64748b;
      --line: #d8e0ec;
      --accent: #2563eb;
      --ok: #15803d;
      --warn: #b45309;
      --danger: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    }}
    .app-shell {{
      display: grid;
      grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
      min-height: 100vh;
    }}
    aside {{
      border-right: 1px solid var(--line);
      background: #fff;
      padding: 22px;
    }}
    main {{ padding: 22px; }}
    h1 {{ margin: 0 0 18px; font-size: 22px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }}
    label {{ display: block; margin: 14px 0 6px; color: var(--muted); font-size: 13px; font-weight: 700; }}
    textarea, select, input {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 11px;
      font: inherit;
      background: #fff;
      color: var(--ink);
    }}
    textarea {{ min-height: 160px; resize: vertical; }}
    button {{
      width: 100%;
      margin-top: 16px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      padding: 11px 13px;
      font-weight: 700;
      cursor: pointer;
    }}
    button:disabled {{ opacity: 0.62; cursor: wait; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 14px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .metric {{ min-height: 96px; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 26px; }}
    .muted {{ color: var(--muted); }}
    .trace-list {{ display: grid; gap: 8px; }}
    .trace-step {{ border: 1px solid #bfdbfe; background: #eff6ff; border-radius: 8px; padding: 10px; }}
    .trace-step strong {{ display: block; color: #1d4ed8; word-break: break-word; }}
    pre {{
      margin: 0;
      overflow: auto;
      max-height: 520px;
      padding: 12px;
      border-radius: 8px;
      background: #0b1020;
      color: #dbeafe;
      font-size: 12px;
      line-height: 1.45;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 9px 7px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); }}
    .numeric {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .map-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 8px; background: #f8fafc; }}
    .map-wrap svg {{ display: block; width: 100%; min-width: 860px; height: auto; }}
    .status-error {{ color: var(--danger); font-weight: 700; }}
    @media (max-width: 920px) {{
      .app-shell {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
    }}
  </style>
</head>
<body>
  <div class="app-shell">
    <aside>
      <h1>UAV Mission Intelligence Demo</h1>
      <form id="mission-form">
        <label for="mission-text">Mission</label>
        <textarea id="mission-text" name="mission_text">{escaped_default}</textarea>
        <label for="provider-select">Provider</label>
        <select id="provider-select" name="provider">
          <option value="offline">offline</option>
          <option value="deepseek">deepseek</option>
          <option value="openai-compatible">openai-compatible</option>
        </select>
        <label for="model-input">Model</label>
        <input id="model-input" name="model">
        <label for="base-url-input">Base URL</label>
        <input id="base-url-input" name="base_url">
        <button id="run-button" type="submit">Run Mission</button>
      </form>
      <p id="status-line" class="muted">Ready</p>
    </aside>
    <main>
      <section class="grid">
        <article class="panel span-4 metric"><h2>Provider</h2><strong id="provider-metric">offline</strong><span id="model-metric" class="muted">rule-based</span></article>
        <article class="panel span-4 metric"><h2>Schema</h2><strong id="schema-metric">ready</strong><span class="muted">mission plan validation</span></article>
        <article class="panel span-4 metric"><h2>Benchmark</h2><strong id="benchmark-metric">loading</strong><span id="benchmark-source" class="muted">provider comparison</span></article>
        <article class="panel span-8" id="mission-map"><h2>Mission Situation Map</h2><div class="map-wrap" id="mission-map-content"></div></article>
        <article class="panel span-4" id="agent-trace"><h2>Agent Trace</h2><div class="trace-list" id="agent-trace-content"></div></article>
        <article class="panel span-6"><h2>Mission JSON</h2><pre id="json-output">{{}}</pre></article>
        <article class="panel span-6"><h2>Benchmark / Provider Comparison</h2><table id="benchmark-table"><thead><tr><th>Provider</th><th class="numeric">Runs</th><th class="numeric">Avg Score</th><th class="numeric">Latency ms</th><th class="numeric">Cost</th></tr></thead><tbody id="benchmark-body"></tbody></table></article>
      </section>
    </main>
  </div>
  <script>
    const form = document.getElementById('mission-form');
    const statusLine = document.getElementById('status-line');
    const runButton = document.getElementById('run-button');

    function setStatus(text, isError) {{
      statusLine.textContent = text;
      statusLine.className = isError ? 'status-error' : 'muted';
    }}

    function escapeText(value) {{
      return String(value ?? '').replace(/[&<>"']/g, (char) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));
    }}

    function renderMission(payload) {{
      document.getElementById('provider-metric').textContent = payload.provider.name;
      document.getElementById('model-metric').textContent = payload.provider.model || 'provider default';
      document.getElementById('schema-metric').textContent = payload.schema_validation.valid ? 'valid' : 'invalid';
      document.getElementById('mission-map-content').innerHTML = payload.mission_svg;
      document.getElementById('json-output').textContent = payload.json_plan;
      document.getElementById('agent-trace-content').innerHTML = payload.agent_trace.map((step) => `
        <div class="trace-step">
          <strong>${{escapeText(step.node)}}</strong>
          <span>${{escapeText(step.status)}} · ${{escapeText(step.message)}}</span>
        </div>`).join('');
    }}

    function renderBenchmark(payload) {{
      document.getElementById('benchmark-metric').textContent = payload.summary.total_scenarios ?? 0;
      document.getElementById('benchmark-source').textContent = payload.source;
      document.getElementById('benchmark-body').innerHTML = payload.provider_comparison.map((row) => `
        <tr>
          <td>${{escapeText(row.provider_label)}}</td>
          <td class="numeric">${{escapeText(row.run_count ?? '')}}</td>
          <td class="numeric">${{Number(row.average_score ?? 0).toFixed(3)}}</td>
          <td class="numeric">${{Number(row.average_latency_ms ?? 0).toFixed(3)}}</td>
          <td class="numeric">${{Number(row.estimated_total_cost ?? 0).toFixed(8)}} ${{escapeText(row.currency ?? 'USD')}}</td>
        </tr>`).join('');
    }}

    async function loadBenchmark() {{
      const response = await fetch('/api/benchmark');
      renderBenchmark(await response.json());
    }}

    async function runMission(event) {{
      event.preventDefault();
      const missionText = document.getElementById('mission-text').value.trim();
      if (!missionText) {{
        setStatus('Mission text is required', true);
        return;
      }}
      runButton.disabled = true;
      setStatus('Running mission', false);
      const response = await fetch('/api/mission', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          mission_text: missionText,
          provider: document.getElementById('provider-select').value,
          model: document.getElementById('model-input').value,
          base_url: document.getElementById('base-url-input').value
        }})
      }});
      const payload = await response.json();
      runButton.disabled = false;
      if (!response.ok) {{
        setStatus(payload.error.message, true);
        return;
      }}
      renderMission(payload);
      setStatus('Mission complete', false);
    }}

    form.addEventListener('submit', runMission);
    loadBenchmark().catch((error) => setStatus(error.message, true));
    form.dispatchEvent(new Event('submit'));
  </script>
</body>
</html>"""


def _normalize_provider(provider: str | None) -> str:
    provider_name = (provider or "offline").strip().lower()
    if provider_name in {"none", "rule-based"}:
        provider_name = "offline"
    if provider_name not in SUPPORTED_PROVIDERS:
        raise DemoError(400, "unsupported_provider", f"unsupported provider: {provider}")
    return provider_name


def _build_demo_provider(
    *,
    provider_name: str,
    model: str | None,
    base_url: str | None,
    provider_factory: Callable,
) -> Any:
    try:
        return provider_factory(provider_name, model=model, base_url=base_url)
    except LLMProviderError as exc:
        raise DemoError(400, "provider_error", _safe_message(str(exc))) from exc


def _normalize_benchmark_report(report: dict[str, Any], *, source: str) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ValueError("benchmark report must be an object")
    normalized = {
        "status": "ok",
        "source": source,
        "summary": report.get("summary", {}),
        "provider_comparison": report.get("provider_comparison", []),
        "difficulty_summary": report.get("difficulty_summary", []),
        "results": report.get("results", []),
    }
    normalized["json_report"] = json.dumps(normalized, ensure_ascii=False, indent=2)
    return normalized


def _strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _safe_message(message: str) -> str:
    return message.replace("Bearer ", "Bearer [redacted] ")
```

- [ ] **Step 4: Run service tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_service -v
```

Expected: PASS for all tests in `tests.test_demo_service`.

- [ ] **Step 5: Commit service layer**

Run:

```powershell
git add src\uav_mission_agent\demo_service.py tests\test_demo_service.py
git commit -m "feat: add interactive demo service layer"
```

Expected: commit includes only `demo_service.py` and `test_demo_service.py`.

---

### Task 2: FastAPI App Boundary

**Files:**
- Create: `src/uav_mission_agent/demo_app.py`
- Create: `tests/test_demo_app.py`

**Interfaces:**
- Consumes:
  - `build_demo_html() -> str`
  - `build_mission_demo_payload(mission_text: str, provider: str = "offline", model: str | None = None, base_url: str | None = None) -> dict[str, Any]`
  - `load_demo_benchmark(report_path: str | Path | None = DEFAULT_BENCHMARK_REPORT, scenario_dir: str | Path = DEFAULT_SCENARIO_DIR) -> dict[str, Any]`
  - `DemoError.to_dict() -> dict[str, Any]`
- Produces:
  - `DEMO_INSTALL_HINT: str`
  - `create_demo_app() -> Any`

- [ ] **Step 1: Write failing FastAPI boundary tests**

Create `tests/test_demo_app.py`:

```python
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:
    TestClient = None


class DemoAppTests(unittest.TestCase):
    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_health_route_reports_ready(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_index_route_returns_demo_html(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("UAV Mission Intelligence Demo", response.text)
        self.assertIn('id="mission-form"', response.text)

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_mission_route_returns_offline_payload(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.post(
            "/api/mission",
            json={
                "mission_text": "Use 2 UAVs to inspect area C and avoid no-fly zone D.",
                "provider": "offline",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["provider"]["name"], "offline")
        self.assertIn("agent_trace", payload)
        self.assertIn("<svg", payload["mission_svg"])

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_mission_route_returns_structured_error_for_empty_mission(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.post("/api/mission", json={"mission_text": " ", "provider": "offline"})

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "invalid_mission")

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_benchmark_route_returns_provider_comparison(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/api/benchmark")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("provider_comparison", payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run FastAPI tests to verify they fail or skip correctly**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_app -v
```

Expected when FastAPI is installed: ERROR with `ModuleNotFoundError: No module named 'uav_mission_agent.demo_app'`.

Expected when FastAPI is not installed: all tests skipped with reason `FastAPI is not installed`.

- [ ] **Step 3: Implement `demo_app.py`**

Create `src/uav_mission_agent/demo_app.py`:

```python
from __future__ import annotations

from typing import Any

from .demo_service import DemoError, build_demo_html, build_mission_demo_payload, load_demo_benchmark


DEMO_INSTALL_HINT = "FastAPI demo requires optional dependencies: pip install 'uav-mission-intelligence-agent[demo]'"


def create_demo_app() -> Any:
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import HTMLResponse, JSONResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(DEMO_INSTALL_HINT) from exc

    app = FastAPI(title="UAV Mission Intelligence Demo")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "uav-mission-agent-demo"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return build_demo_html()

    @app.get("/api/benchmark")
    def benchmark() -> dict[str, Any]:
        return load_demo_benchmark()

    @app.post("/api/mission")
    async def mission(request: Request):
        try:
            body = await request.json()
            return build_mission_demo_payload(
                mission_text=str(body.get("mission_text", "")),
                provider=str(body.get("provider", "offline")),
                model=body.get("model"),
                base_url=body.get("base_url"),
            )
        except DemoError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"status": "error", "error": exc.to_dict()},
            )

    return app
```

- [ ] **Step 4: Run FastAPI tests to verify they pass or skip correctly**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_app -v
```

Expected when FastAPI is installed: PASS.

Expected when FastAPI is not installed: tests skipped with no failures.

- [ ] **Step 5: Commit FastAPI boundary**

Run:

```powershell
git add src\uav_mission_agent\demo_app.py tests\test_demo_app.py
git commit -m "feat: expose interactive demo FastAPI app"
```

Expected: commit includes only `demo_app.py` and `test_demo_app.py`.

---

### Task 3: Demo CLI And Packaging

**Files:**
- Create: `src/uav_mission_agent/demo_cli.py`
- Create: `tests/test_demo_cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes:
  - `load_env_file(path: str | Path) -> dict[str, str]`
  - `create_demo_app() -> Any`
- Produces:
  - `build_parser() -> argparse.ArgumentParser`
  - `run_server(host: str, port: int) -> None`
  - `main(argv: list[str] | None = None, server_runner=run_server) -> None`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_demo_cli.py`:

```python
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.demo_cli import build_parser, main


class DemoCliTests(unittest.TestCase):
    def test_parser_defaults_to_localhost_and_port_8000(self):
        args = build_parser().parse_args([])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8000)
        self.assertIsNone(args.env_file)

    def test_main_loads_env_file_and_calls_server_runner(self):
        calls = []

        def fake_runner(host, port):
            calls.append({"host": host, "port": port})

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "deepseek.env"
            env_path.write_text("DEEPSEEK_API_KEY=demo-key\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                main(
                    ["--host", "0.0.0.0", "--port", "8100", "--env-file", str(env_path)],
                    server_runner=fake_runner,
                )

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "demo-key")

        self.assertEqual(calls, [{"host": "0.0.0.0", "port": 8100}])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_cli -v
```

Expected: ERROR with `ModuleNotFoundError: No module named 'uav_mission_agent.demo_cli'`.

- [ ] **Step 3: Implement `demo_cli.py`**

Create `src/uav_mission_agent/demo_cli.py`:

```python
from __future__ import annotations

import argparse

from .demo_service import load_env_file


DEMO_INSTALL_HINT = "FastAPI demo requires optional dependencies: pip install 'uav-mission-intelligence-agent[demo]'"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the UAV Mission Intelligence interactive demo.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the demo server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the demo server.")
    parser.add_argument("--env-file", help="Optional KEY=value env file for provider credentials.")
    return parser


def run_server(host: str, port: int) -> None:
    try:
        import uvicorn
        from .demo_app import create_demo_app
    except ModuleNotFoundError as exc:
        raise RuntimeError(DEMO_INSTALL_HINT) from exc

    uvicorn.run(create_demo_app(), host=host, port=port)


def main(argv: list[str] | None = None, server_runner=run_server) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.env_file:
        load_env_file(args.env_file)
    server_runner(args.host, args.port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update packaging**

Modify `pyproject.toml` so the relevant sections are:

```toml
[project.optional-dependencies]
langgraph = ["langgraph>=0.2"]
rag-faiss = ["faiss-cpu>=1.8"]
rag-chroma = ["chromadb>=0.5"]
rag = [
    "faiss-cpu>=1.8",
    "chromadb>=0.5",
]
demo = [
    "fastapi>=0.100",
    "uvicorn>=0.23",
]

[project.scripts]
uav-mission-agent = "uav_mission_agent.cli:main"
uav-mission-agent-demo = "uav_mission_agent.demo_cli:main"
```

- [ ] **Step 5: Run CLI tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_cli -v
```

Expected: PASS.

- [ ] **Step 6: Commit CLI and packaging**

Run:

```powershell
git add pyproject.toml src\uav_mission_agent\demo_cli.py tests\test_demo_cli.py
git commit -m "feat: add interactive demo launcher"
```

Expected: commit includes only `pyproject.toml`, `demo_cli.py`, and `test_demo_cli.py`.

---

### Task 4: README And Engineering Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/engineering.md`
- Modify: `tests/test_readme_assets.py`

**Interfaces:**
- Consumes:
  - `uav-mission-agent-demo --host 127.0.0.1 --port 8000`
  - `uav-mission-agent-demo --env-file D:\epacode\working\.secrets\deepseek.env`
- Produces:
  - README section `## Interactive Demo / 交互式 Demo`
  - Engineering section `## Interactive Demo`

- [ ] **Step 1: Write failing documentation tests**

Modify `tests/test_readme_assets.py` by adding this test method inside the existing test class:

```python
    def test_readme_documents_interactive_demo(self):
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertIn("Interactive Demo / 交互式 Demo", readme)
        self.assertIn("pip install -e \".[demo]\"", readme)
        self.assertIn("uav-mission-agent-demo --host 127.0.0.1 --port 8000", readme)
        self.assertIn("uav-mission-agent-demo --env-file D:\\epacode\\working\\.secrets\\deepseek.env", readme)
        self.assertIn("Agent trace", readme)
        self.assertIn("provider comparison", readme)
```

- [ ] **Step 2: Run documentation test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_readme_assets -v
```

Expected: FAIL because README does not yet contain `Interactive Demo / 交互式 Demo`.

- [ ] **Step 3: Update README**

Add this section after the static dashboard section:

```markdown
## Interactive Demo / 交互式 Demo

交互式 demo 提供一个本地 FastAPI + HTML 控制台，可以输入 UAV 任务、选择 provider、查看 Agent trace、结构化 JSON 输出、Benchmark v2/provider comparison 和任务态势图。

The interactive demo provides a local FastAPI + HTML console for entering UAV missions, selecting a provider, and inspecting Agent trace, structured JSON output, Benchmark v2/provider comparison, and the mission situation map.

Install the optional demo dependencies:

```powershell
pip install -e ".[demo]"
```

Run the offline demo:

```powershell
uav-mission-agent-demo --host 127.0.0.1 --port 8000
```

Run with the existing DeepSeek env file:

```powershell
uav-mission-agent-demo --env-file D:\epacode\working\.secrets\deepseek.env
```

Open `http://127.0.0.1:8000` after the server starts. The default `offline` provider requires no API key. Selecting `deepseek` uses `DEEPSEEK_API_KEY` from the environment or env file.
```

Update the module table with:

```markdown
| `demo_service.py` | 为交互 demo 构建任务 payload、benchmark payload、HTML 页面和 env-file 加载。<br>Build mission payloads, benchmark payloads, HTML, and env-file loading for the interactive demo. |
| `demo_app.py` | 暴露可选 FastAPI demo app 和 JSON API。<br>Expose the optional FastAPI demo app and JSON API. |
| `demo_cli.py` | 提供 `uav-mission-agent-demo` 本地服务启动入口。<br>Provide the local `uav-mission-agent-demo` server launcher. |
```

Replace the roadmap line that says interactive Streamlit/FastAPI is future work with:

```markdown
- 交互式 FastAPI + HTML demo 已提供，后续可扩展为多任务会话和更丰富的态势回放。<br>
  The interactive FastAPI + HTML demo is available; future work can expand it into multi-mission sessions and richer situation replay.
```

- [ ] **Step 4: Update engineering notes**

Add this section before `## Testing and CI` in `docs/engineering.md`:

```markdown
## Interactive Demo

The interactive demo is a thin service/UI layer over the existing offline-first Agent workflow.

Run it with optional dependencies:

```powershell
python -m pip install -e ".[demo]"
uav-mission-agent-demo --host 127.0.0.1 --port 8000
```

Use the DeepSeek env file without printing secrets:

```powershell
uav-mission-agent-demo --env-file D:\epacode\working\.secrets\deepseek.env
```

Demo responsibilities:

- `demo_service.py`: validates mission input, builds offline or live-provider mission payloads, renders the mission SVG, loads saved provider comparison reports, and falls back to offline Benchmark v2.
- `demo_app.py`: exposes `GET /`, `GET /api/health`, `GET /api/benchmark`, and `POST /api/mission`.
- `demo_cli.py`: loads a simple `KEY=value` env file and starts Uvicorn.

The default tests exercise `demo_service.py` and `demo_cli.py` without FastAPI. FastAPI route tests are skipped when demo dependencies are not installed.
```

Add these rows to the architecture module table:

```markdown
| `demo_service.py` | Dependency-free payload, benchmark, env-file, and HTML helpers for the interactive demo. |
| `demo_app.py` | Optional FastAPI app for the interactive demo. |
| `demo_cli.py` | Local Uvicorn launcher for the interactive demo. |
```

- [ ] **Step 5: Run documentation tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_readme_assets -v
```

Expected: PASS.

- [ ] **Step 6: Commit documentation**

Run:

```powershell
git add README.md docs\engineering.md tests\test_readme_assets.py
git commit -m "docs: document interactive demo"
```

Expected: commit includes only README, engineering notes, and README tests.

---

### Task 5: Full Verification And Local Demo Smoke Test

**Files:**
- No new source files.
- The final commit is needed only if verification finds a defect that requires a fix.

**Interfaces:**
- Consumes:
  - `build_mission_demo_payload(mission_text: str, provider: str = "offline", model: str | None = None, base_url: str | None = None) -> dict[str, Any]`
  - `create_demo_app() -> Any`
  - `uav-mission-agent-demo --host 127.0.0.1 --port 8000`

- [ ] **Step 1: Run focused demo test suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest tests.test_demo_service tests.test_demo_cli tests.test_demo_app -v
```

Expected: PASS, with FastAPI route tests either passing or being skipped when FastAPI is not installed.

- [ ] **Step 2: Run full unit test suite**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m unittest discover -s tests -v
```

Expected: PASS for all default tests.

- [ ] **Step 3: Check whether demo dependencies are installed**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -c "import fastapi, uvicorn; print('demo dependencies available')"
```

Expected when installed: prints `demo dependencies available`.

Expected when not installed: `ModuleNotFoundError` for `fastapi` or `uvicorn`. In that case, do not mark browser/server smoke testing complete; report that the demo server can be run after installing `.[demo]`.

- [ ] **Step 4: Start the local demo server when dependencies are installed**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m uav_mission_agent.demo_cli --host 127.0.0.1 --port 8000
```

Expected: Uvicorn starts on `http://127.0.0.1:8000`. Keep the server running only long enough to perform the smoke requests, then stop it.

- [ ] **Step 5: Smoke test health and page when server is running**

Run in a second PowerShell session:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-WebRequest http://127.0.0.1:8000/ | Select-Object -ExpandProperty StatusCode
```

Expected: health response contains `status: ok`; page status code is `200`.

- [ ] **Step 6: Inspect git status**

Run:

```powershell
git status -sb
```

Expected: clean working tree after all intended commits, or only intentional uncommitted verification artifacts that should not be committed.

- [ ] **Step 7: Push after implementation is complete**

Run:

```powershell
git push
```

Expected: remote `main` receives the design, plan, and implementation commits.
