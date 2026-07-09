from __future__ import annotations

from collections.abc import Callable
import html
import json
import os
from pathlib import Path
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
    scenario_loader: Callable = load_scenarios,
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
    rendered = f"""<!doctype html>
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
      .span-4, .span-6, .span-8 {{ grid-column: span 12; }}
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
          <span>${{escapeText(step.status)}} - ${{escapeText(step.message)}}</span>
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
    return "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"


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
