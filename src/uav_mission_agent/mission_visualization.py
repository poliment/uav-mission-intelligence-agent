from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def render_mission_execution_svg(plan: dict[str, Any]) -> str:
    config = plan.get("mission_config", {})
    task = plan.get("task", {})
    uav_count = _bounded_uav_count(config.get("uav_count", task.get("drone_count", 1)))
    search_area = _first_text(config.get("search_areas", []), "Area A")
    avoid_zone = _first_text(config.get("avoid_zones", []), "NFZ B")
    weak_comm = "low_bandwidth_coordination" in task.get("constraints", []) or (
        config.get("coordination_mode") == "distributed_low_bandwidth"
    )
    uavs = _render_uavs(uav_count)
    comm_label = "Weak Communication" if weak_comm else "Nominal Communication"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="520" viewBox="0 0 1180 520" role="img" aria-labelledby="mission-map-title mission-map-desc">
  <title id="mission-map-title">Mission Execution Visualization</title>
  <desc id="mission-map-desc">UAV mission map showing search area, no-fly zone, target point, planned route, replanned route, coverage path, and communication condition.</desc>
  <rect width="1180" height="520" rx="8" fill="#f8fafc"/>
  <rect x="36" y="38" width="760" height="430" rx="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>
  <text x="58" y="70" fill="#334155" font-family="Arial, sans-serif" font-size="18" font-weight="700">Operating Boundary</text>
  {_render_grid()}
  <rect x="112" y="116" width="392" height="250" rx="6" fill="#dbeafe" stroke="#2563eb" stroke-width="2" opacity="0.78"/>
  <text x="132" y="145" fill="#1d4ed8" font-family="Arial, sans-serif" font-size="16" font-weight="700">Search Area: {html.escape(search_area)}</text>
  <rect x="430" y="168" width="170" height="120" rx="6" fill="#fee2e2" stroke="#dc2626" stroke-width="2" opacity="0.9"/>
  <text x="448" y="196" fill="#991b1b" font-family="Arial, sans-serif" font-size="15" font-weight="700">No-Fly Zone: {html.escape(avoid_zone)}</text>
  <circle cx="642" cy="330" r="16" fill="#f59e0b" stroke="#92400e" stroke-width="3"/>
  <path d="M642 314 L647 328 L662 328 L650 337 L655 352 L642 343 L629 352 L634 337 L622 328 L637 328 Z" fill="#fff7ed"/>
  <text x="610" y="370" fill="#92400e" font-family="Arial, sans-serif" font-size="15" font-weight="700">Target Point</text>
  <polyline points="82,410 184,330 292,250 414,226 560,228 700,276" fill="none" stroke="#0f172a" stroke-width="4" stroke-linecap="round" stroke-dasharray="10 8"/>
  <text x="86" y="438" fill="#0f172a" font-family="Arial, sans-serif" font-size="14">Planned Route</text>
  <polyline points="82,410 176,350 284,310 408,316 520,360 700,276" fill="none" stroke="#16a34a" stroke-width="5" stroke-linecap="round"/>
  <text x="315" y="405" fill="#166534" font-family="Arial, sans-serif" font-size="14" font-weight="700">Replanned Route</text>
  <path d="M145 170 C210 130, 275 130, 340 172 S456 212, 492 156" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" opacity="0.85"/>
  <path d="M152 236 C224 196, 310 196, 382 236 S468 284, 506 235" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" opacity="0.85"/>
  <text x="150" y="104" fill="#1d4ed8" font-family="Arial, sans-serif" font-size="14">Coverage Path</text>
  {uavs}
  {_render_side_panel(uav_count, comm_label)}
</svg>"""
    return "\n".join(line.rstrip() for line in svg.splitlines()) + "\n"


def write_mission_visualization_asset(output_path: str | Path, plan: dict[str, Any]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_mission_execution_svg(plan), encoding="utf-8")
    return path


def _bounded_uav_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 1
    return max(1, min(3, count))


def _first_text(values: Any, fallback: str) -> str:
    if isinstance(values, list) and values:
        return str(values[0])
    return fallback


def _render_grid() -> str:
    lines = []
    for x in range(96, 780, 76):
        lines.append(f'<line x1="{x}" y1="92" x2="{x}" y2="452" stroke="#e2e8f0" stroke-width="1"/>')
    for y in range(100, 450, 58):
        lines.append(f'<line x1="58" y1="{y}" x2="770" y2="{y}" stroke="#e2e8f0" stroke-width="1"/>')
    return "\n  ".join(lines)


def _render_uavs(count: int) -> str:
    positions = [(86, 410), (176, 350), (284, 310)]
    rendered = []
    for index, (x, y) in enumerate(positions[:count], start=1):
        rendered.append(
            f"""<g aria-label="UAV-{index}">
    <circle cx="{x}" cy="{y}" r="18" fill="#0f766e" stroke="#042f2e" stroke-width="3"/>
    <path d="M{x - 18} {y} H{x + 18} M{x} {y - 18} V{y + 18}" stroke="#ccfbf1" stroke-width="3" stroke-linecap="round"/>
    <text x="{x - 22}" y="{y - 28}" fill="#134e4a" font-family="Arial, sans-serif" font-size="13" font-weight="700">UAV-{index}</text>
  </g>"""
        )
    return "\n  ".join(rendered)


def _render_side_panel(uav_count: int, comm_label: str) -> str:
    return f"""<rect x="830" y="48" width="306" height="410" rx="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>
  <text x="858" y="86" fill="#0f172a" font-family="Arial, sans-serif" font-size="20" font-weight="700">Mission Status</text>
  <rect x="858" y="112" width="238" height="46" rx="6" fill="#ecfdf5" stroke="#86efac"/>
  <text x="876" y="141" fill="#166534" font-family="Arial, sans-serif" font-size="15" font-weight="700">Task Progress: 72%</text>
  <rect x="858" y="178" width="238" height="46" rx="6" fill="#eff6ff" stroke="#93c5fd"/>
  <text x="876" y="207" fill="#1d4ed8" font-family="Arial, sans-serif" font-size="15" font-weight="700">Active UAVs: {uav_count}</text>
  <rect x="858" y="244" width="238" height="46" rx="6" fill="#fff7ed" stroke="#fdba74"/>
  <text x="876" y="273" fill="#9a3412" font-family="Arial, sans-serif" font-size="15" font-weight="700">{html.escape(comm_label)}</text>
  <path d="M890 332 C924 300, 972 300, 1006 332" fill="none" stroke="#f97316" stroke-width="4"/>
  <path d="M912 356 C934 336, 962 336, 984 356" fill="none" stroke="#f97316" stroke-width="4"/>
  <circle cx="948" cy="382" r="8" fill="#f97316"/>
  <text x="858" y="426" fill="#475569" font-family="Arial, sans-serif" font-size="14">Status labels are derived from the agent plan and mission constraints.</text>"""
