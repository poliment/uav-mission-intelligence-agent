from __future__ import annotations

import html
import json
from pathlib import Path

from .agent_graph import run_agent_workflow
from .benchmark_v2 import run_benchmark_v2
from .scenario_loader import load_scenarios


DEFAULT_MISSION_TEXT = "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
DEFAULT_SCENARIO_DIR = Path("data") / "scenarios"


def build_dashboard_html(
    mission_text: str = DEFAULT_MISSION_TEXT,
    scenario_dir: str | Path = DEFAULT_SCENARIO_DIR,
) -> str:
    plan = run_agent_workflow(mission_text)
    benchmark = run_benchmark_v2(load_scenarios(scenario_dir))
    return _render_dashboard(plan, benchmark)


def write_dashboard(
    output_path: str | Path,
    mission_text: str = DEFAULT_MISSION_TEXT,
    scenario_dir: str | Path = DEFAULT_SCENARIO_DIR,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_dashboard_html(mission_text, scenario_dir), encoding="utf-8")
    return path


def _render_dashboard(plan: dict, benchmark: dict) -> str:
    mission = plan["task"]["raw_request"]
    summary = benchmark["summary"]
    json_plan = json.dumps(plan, ensure_ascii=False, indent=2)
    json_benchmark = json.dumps(benchmark, ensure_ascii=False, indent=2)
    rendered = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>UAV Mission Intelligence Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --ink: #152033;
      --muted: #667085;
      --line: #d9e2ef;
      --blue: #1d4ed8;
      --green: #16803c;
      --amber: #b7791f;
      --soft-blue: #e8f1ff;
      --soft-green: #eaf7ef;
      --soft-amber: #fff6df;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.5;
    }}
    header {{
      padding: 32px 40px 24px;
      background: #0f172a;
      color: #fff;
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    header p {{
      max-width: 920px;
      margin: 0;
      color: #cbd5e1;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }}
    .span-3 {{ grid-column: span 3; }}
    .span-4 {{ grid-column: span 4; }}
    .span-6 {{ grid-column: span 6; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .metric {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-height: 90px;
    }}
    .metric strong {{
      font-size: 32px;
    }}
    .muted {{ color: var(--muted); }}
    .mission-text {{
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      font-size: 15px;
    }}
    .node-flow {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .node {{
      border: 1px solid #bfd2ef;
      background: var(--soft-blue);
      border-radius: 8px;
      padding: 12px;
      min-height: 132px;
    }}
    .node-name {{
      font-weight: 700;
      color: var(--blue);
      word-break: break-word;
    }}
    .node small {{
      display: block;
      margin-top: 8px;
      color: var(--muted);
    }}
    .pill-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .pill {{
      border-radius: 999px;
      padding: 5px 9px;
      background: var(--soft-green);
      border: 1px solid #bfe7cc;
      color: var(--green);
      font-size: 13px;
      white-space: nowrap;
    }}
    .list {{
      margin: 0;
      padding-left: 18px;
    }}
    .list li + li {{ margin-top: 8px; }}
    .score-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      margin-top: 10px;
    }}
    .score-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 8px;
    }}
    .score-bar {{
      height: 10px;
      border-radius: 999px;
      background: #e5e7eb;
      overflow: hidden;
    }}
    .score-fill {{
      height: 100%;
      background: linear-gradient(90deg, #2563eb, #16a34a);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 700;
    }}
    .numeric {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    pre {{
      overflow: auto;
      max-height: 420px;
      padding: 14px;
      background: #0b1020;
      color: #dbeafe;
      border-radius: 8px;
      font-size: 12px;
      line-height: 1.45;
    }}
    @media (max-width: 860px) {{
      header {{ padding: 26px 22px; }}
      main {{ padding: 16px; }}
      .span-3, .span-4, .span-6, .span-8, .span-12 {{ grid-column: span 12; }}
      .node-flow {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>UAV Mission Intelligence Dashboard</h1>
    <p>A local visualization page for mission input, traceable Agent nodes, planning output, and benchmark scores.</p>
  </header>
  <main>
    <section class="grid">
      {_render_metric_cards(summary)}
      <article class="panel span-12" id="mission-input">
        <h2>Mission Input</h2>
        <div class="mission-text">{html.escape(mission)}</div>
      </article>
      <article class="panel span-12" id="agent-flow">
        <h2>Agent Node Flow</h2>
        <div class="node-flow">
          {_render_agent_nodes(plan["agent_trace"])}
        </div>
      </article>
      <article class="panel span-6" id="planning-output">
        <h2>Planning Recommendations</h2>
        {_render_list(plan["recommendations"])}
      </article>
      <article class="panel span-6" id="risk-output">
        <h2>Risk Explanation</h2>
        {_render_list(plan["risks"])}
      </article>
      <article class="panel span-6" id="mission-config">
        <h2>Mission Config</h2>
        {_render_config_pills(plan["mission_config"])}
      </article>
      <article class="panel span-6" id="benchmark-scores">
        <h2>Benchmark Scores</h2>
        {_render_scores(benchmark["results"])}
      </article>
      <article class="panel span-6" id="provider-comparison">
        <h2>Provider Comparison</h2>
        {_render_provider_comparison(benchmark["provider_comparison"])}
      </article>
      <article class="panel span-6" id="cost-summary">
        <h2>Cost Summary</h2>
        {_render_cost_summary(benchmark)}
      </article>
      <article class="panel span-6">
        <h2>Agent JSON</h2>
        <pre>{html.escape(json_plan)}</pre>
      </article>
      <article class="panel span-6">
        <h2>Benchmark v2 JSON</h2>
        <pre>{html.escape(json_benchmark)}</pre>
      </article>
    </section>
  </main>
</body>
</html>
"""
    return "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"


def _render_metric_cards(summary: dict) -> str:
    average_score = summary.get("average_score", 0)
    total = summary.get("total_scenarios", 0)
    providers = summary.get("provider_count", 0)
    passed = summary.get("passed_runs", summary.get("passed_scenarios", 0))
    total_cost = summary.get("estimated_total_cost", 0.0)
    currency = summary.get("currency", "USD")
    return f"""
      <article class="panel span-3 metric">
        <span class="muted">average_score</span>
        <strong>{average_score:.2f}</strong>
        <span>Mean benchmark scenario score</span>
      </article>
      <article class="panel span-3 metric">
        <span class="muted">total_scenarios</span>
        <strong>{total}</strong>
        <span>UAV mission benchmark cases</span>
      </article>
      <article class="panel span-3 metric">
        <span class="muted">providers</span>
        <strong>{providers}</strong>
        <span>Compared execution providers</span>
      </article>
      <article class="panel span-3 metric">
        <span class="muted">estimated_total_cost</span>
        <strong>{total_cost:.6f}</strong>
        <span>{html.escape(currency)} estimated total cost, passed_runs: {passed}</span>
      </article>
    """


def _render_provider_comparison(rows: list[dict]) -> str:
    if not rows:
        return "<p class=\"muted\">No provider comparison rows.</p>"
    rendered_rows = []
    for row in rows:
        rendered_rows.append(
            f"""
            <tr>
              <td>{html.escape(row.get("provider_label", ""))}</td>
              <td>{html.escape(str(row.get("model", "")))}</td>
              <td class="numeric">{float(row.get("average_score", 0)):.2f}</td>
              <td class="numeric">{float(row.get("average_latency_ms", 0)):.3f}</td>
              <td class="numeric">{float(row.get("estimated_total_cost", 0)):.8f} {html.escape(row.get("currency", "USD"))}</td>
            </tr>
            """
        )
    return f"""
      <table>
        <thead>
          <tr>
            <th>Provider</th>
            <th>Model</th>
            <th class="numeric">Avg Score</th>
            <th class="numeric">Latency ms</th>
            <th class="numeric">Estimated Cost</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rendered_rows)}
        </tbody>
      </table>
    """


def _render_cost_summary(benchmark: dict) -> str:
    summary = benchmark.get("summary", {})
    results = benchmark.get("results", [])
    prompt_tokens = sum(result.get("token_usage", {}).get("prompt_tokens", 0) for result in results)
    completion_tokens = sum(result.get("token_usage", {}).get("completion_tokens", 0) for result in results)
    total_tokens = sum(result.get("token_usage", {}).get("total_tokens", 0) for result in results)
    currency = summary.get("currency", "USD")
    total_cost = summary.get("estimated_total_cost", 0.0)
    return f"""
      <table>
        <tbody>
          <tr><th>prompt_tokens</th><td class="numeric">{prompt_tokens}</td></tr>
          <tr><th>completion_tokens</th><td class="numeric">{completion_tokens}</td></tr>
          <tr><th>total_tokens</th><td class="numeric">{total_tokens}</td></tr>
          <tr><th>estimated_total_cost</th><td class="numeric">{float(total_cost):.8f} {html.escape(currency)}</td></tr>
        </tbody>
      </table>
      <p class="muted">Offline runs have zero billable LLM tokens. Live provider cost is estimated from returned usage metadata and configured pricing.</p>
    """


def _render_agent_nodes(trace: list[dict]) -> str:
    return "\n".join(
        f"""
          <div class="node">
            <div class="node-name">{html.escape(step["node"])}</div>
            <small>Status: {html.escape(step["status"])}</small>
            <small>Inputs: {html.escape(", ".join(step["input_keys"]))}</small>
            <small>Outputs: {html.escape(", ".join(step["output_keys"]))}</small>
            <small>{html.escape(step["message"])}</small>
          </div>
        """
        for step in trace
    )


def _render_list(items: list[str]) -> str:
    return "<ul class=\"list\">" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def _render_config_pills(config: dict) -> str:
    values = [
        ("uav_count", str(config.get("uav_count", ""))),
        ("coordination_mode", str(config.get("coordination_mode", ""))),
        ("planning_policy", str(config.get("planning_policy", ""))),
        ("search_areas", ", ".join(config.get("search_areas", []))),
        ("avoid_zones", ", ".join(config.get("avoid_zones", [])) or "none"),
    ]
    return "<div class=\"pill-row\">" + "".join(
        f"<span class=\"pill\">{html.escape(key)}: {html.escape(value)}</span>" for key, value in values
    ) + "</div>"


def _render_scores(results: list[dict]) -> str:
    cards = []
    for result in results:
        score = float(result.get("score", 0))
        width = max(0, min(100, int(score * 100)))
        cards.append(
            f"""
            <div class="score-card">
              <div class="score-head">
                <strong>{html.escape(result["scenario_id"])}</strong>
                <span>{score:.2f}</span>
              </div>
              <div class="score-bar"><div class="score-fill" style="width: {width}%"></div></div>
              <p class="muted">{html.escape(result.get("name", ""))}</p>
            </div>
            """
        )
    return "\n".join(cards)
