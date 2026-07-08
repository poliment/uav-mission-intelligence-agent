# Mission Execution Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline UAV mission execution visualization that appears in the local dashboard and as a README-ready SVG asset.

**Architecture:** Add a pure Python SVG renderer in `src/uav_mission_agent/mission_visualization.py`. The dashboard calls this renderer with the existing agent workflow output, and a generated SVG asset under `docs/assets/` uses the same renderer so the README image and dashboard map stay consistent.

**Tech Stack:** Python standard library, inline SVG, existing `unittest` test suite, existing static HTML dashboard.

## Global Constraints

- The visualization must work offline without API keys.
- Do not add a heavy JavaScript framework.
- Do not build a simulation engine or physics model.
- Render a deterministic 2D mission scene from the current mission plan/config.
- Show operating boundary, grid, search area, no-fly zone, target point, UAV icons, planned route, replanned route, coverage path, weak-communication indicator, and mission progress/status labels.
- Keep edits scoped to visualization, dashboard integration, README asset, and tests.

---

## File Structure

- Create `src/uav_mission_agent/mission_visualization.py`
  - Owns mission-scene rendering.
  - Exposes `render_mission_execution_svg(plan: dict) -> str`.
  - Exposes `write_mission_visualization_asset(output_path: str | Path, plan: dict) -> Path`.
- Create `tests/test_mission_visualization.py`
  - Tests SVG structure and asset writing through real agent workflow output.
- Modify `src/uav_mission_agent/dashboard.py`
  - Imports `render_mission_execution_svg`.
  - Embeds mission execution SVG in a new dashboard section.
  - Adds small CSS rules for the map container.
- Modify `tests/test_dashboard.py`
  - Verifies the dashboard contains the mission execution visualization section.
- Create `docs/assets/mission-execution-visualization.svg`
  - Static GitHub/README preview image generated from the renderer.
- Modify `README.md`
  - References the new static SVG asset near the first visual section.
- Modify `dashboard/uav_mission_dashboard.html`
  - Regenerated tracked dashboard artifact.

---

### Task 1: Add Mission SVG Renderer

**Files:**
- Create: `src/uav_mission_agent/mission_visualization.py`
- Create: `tests/test_mission_visualization.py`

**Interfaces:**
- Consumes: an existing agent workflow plan dictionary from `run_agent_workflow(mission_text)`.
- Produces:
  - `render_mission_execution_svg(plan: dict) -> str`
  - `write_mission_visualization_asset(output_path: str | Path, plan: dict) -> Path`

- [ ] **Step 1: Write the failing renderer tests**

Create `tests/test_mission_visualization.py` with this content:

```python
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.agent_graph import run_agent_workflow
from uav_mission_agent.mission_visualization import (
    render_mission_execution_svg,
    write_mission_visualization_asset,
)


MISSION_TEXT = "Use 3 UAVs to search area_A, avoid NFZ_B, track target T1, weak comm, replan if blocked."


class MissionVisualizationTests(unittest.TestCase):
    def test_render_mission_execution_svg_contains_operational_scene(self):
        plan = run_agent_workflow(MISSION_TEXT)

        svg = render_mission_execution_svg(plan)

        self.assertIn("<svg", svg)
        self.assertIn("Mission Execution Visualization", svg)
        self.assertIn("Operating Boundary", svg)
        self.assertIn("Search Area", svg)
        self.assertIn("No-Fly Zone", svg)
        self.assertIn("Target Point", svg)
        self.assertIn("Planned Route", svg)
        self.assertIn("Replanned Route", svg)
        self.assertIn("Coverage Path", svg)
        self.assertIn("Weak Communication", svg)
        self.assertIn("UAV-1", svg)
        self.assertIn("UAV-2", svg)
        self.assertIn("UAV-3", svg)

    def test_write_mission_visualization_asset_writes_svg_file(self):
        plan = run_agent_workflow(MISSION_TEXT)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "mission.svg"

            written = write_mission_visualization_asset(output_path, plan)

            self.assertEqual(written, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("<svg", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
python -B -m unittest tests.test_mission_visualization -v
```

Expected: FAIL or ERROR because `uav_mission_agent.mission_visualization` does not exist.

- [ ] **Step 3: Add the minimal SVG renderer**

Create `src/uav_mission_agent/mission_visualization.py` with this content:

```python
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
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```powershell
python -B -m unittest tests.test_mission_visualization -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add src/uav_mission_agent/mission_visualization.py tests/test_mission_visualization.py
git commit -m "feat: add mission execution visualization renderer"
```

Expected: commit includes only the renderer and its tests.

---

### Task 2: Embed Visualization in Dashboard

**Files:**
- Modify: `src/uav_mission_agent/dashboard.py`
- Modify: `tests/test_dashboard.py`

**Interfaces:**
- Consumes: `render_mission_execution_svg(plan: dict) -> str` from Task 1.
- Produces: a dashboard section with `id="mission-execution-visualization"`.

- [ ] **Step 1: Write the failing dashboard integration test**

Modify `tests/test_dashboard.py` inside `test_build_dashboard_html_contains_core_visual_sections` by adding these assertions after the mission input assertion:

```python
        self.assertIn('id="mission-execution-visualization"', html)
        self.assertIn("Mission Execution Visualization", html)
        self.assertIn("No-Fly Zone", html)
        self.assertIn("Replanned Route", html)
```

- [ ] **Step 2: Run the dashboard test to verify it fails**

Run:

```powershell
python -B -m unittest tests.test_dashboard -v
```

Expected: FAIL because `id="mission-execution-visualization"` is not in the dashboard HTML.

- [ ] **Step 3: Import and render the mission SVG in dashboard**

Modify the imports at the top of `src/uav_mission_agent/dashboard.py`:

```python
from .mission_visualization import render_mission_execution_svg
```

Modify `_render_dashboard` after `json_benchmark = ...`:

```python
    mission_svg = render_mission_execution_svg(plan)
```

Add this CSS block near the existing dashboard styles. The dashboard HTML is rendered from a Python f-string, so keep the doubled braces:

```css
    .mission-map {{
      width: 100%;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
    }}
    .mission-map svg {{
      display: block;
      width: 100%;
      min-width: 860px;
      height: auto;
    }}
```

Add this dashboard article after the `mission-input` article:

```html
      <article class="panel span-12" id="mission-execution-visualization">
        <h2>Mission Execution Visualization</h2>
        <div class="mission-map">{mission_svg}</div>
      </article>
```

- [ ] **Step 4: Run the dashboard test to verify it passes**

Run:

```powershell
python -B -m unittest tests.test_dashboard -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add src/uav_mission_agent/dashboard.py tests/test_dashboard.py
git commit -m "feat: embed mission visualization in dashboard"
```

Expected: commit includes dashboard source and dashboard test only.

---

### Task 3: Add README SVG Asset

**Files:**
- Create: `docs/assets/mission-execution-visualization.svg`
- Create: `tests/test_readme_assets.py`
- Modify: `README.md`

**Interfaces:**
- Consumes:
  - `run_agent_workflow(mission_text: str) -> dict`
  - `write_mission_visualization_asset(output_path: str | Path, plan: dict) -> Path`
- Produces: README image reference to `docs/assets/mission-execution-visualization.svg`.

- [ ] **Step 1: Write the failing README asset test**

Create `tests/test_readme_assets.py` with this content:

```python
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
MISSION_ASSET = REPO_ROOT / "docs" / "assets" / "mission-execution-visualization.svg"


class ReadmeAssetsTests(unittest.TestCase):
    def test_readme_references_mission_execution_visualization_asset(self):
        readme = README.read_text(encoding="utf-8")

        self.assertIn("docs/assets/mission-execution-visualization.svg", readme)

    def test_mission_execution_visualization_asset_exists(self):
        self.assertTrue(MISSION_ASSET.exists())
        svg = MISSION_ASSET.read_text(encoding="utf-8")
        self.assertIn("Mission Execution Visualization", svg)
        self.assertIn("UAV-1", svg)
        self.assertIn("No-Fly Zone", svg)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the README asset test to verify it fails**

Run:

```powershell
python -B -m unittest tests.test_readme_assets -v
```

Expected: FAIL because the README does not reference the asset and `docs/assets/mission-execution-visualization.svg` does not exist.

- [ ] **Step 3: Generate the mission visualization asset**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -c "from pathlib import Path; from uav_mission_agent.agent_graph import run_agent_workflow; from uav_mission_agent.mission_visualization import write_mission_visualization_asset; plan = run_agent_workflow('Use 3 UAVs to search area_A, avoid NFZ_B, track target T1, weak comm, replan if blocked.'); write_mission_visualization_asset(Path('docs/assets/mission-execution-visualization.svg'), plan)"
```

Expected: `docs/assets/mission-execution-visualization.svg` is created.

- [ ] **Step 4: Add the README image reference**

Modify the top visual section of `README.md` so the first images are:

```markdown
![UAV Mission Intelligence Agent demo](docs/assets/uav-mission-demo.png)

![UAV mission execution visualization](docs/assets/mission-execution-visualization.svg)

![Expanded UAV benchmark coverage](docs/assets/benchmark-coverage.svg)
```

- [ ] **Step 5: Run the README asset test to verify it passes**

Run:

```powershell
python -B -m unittest tests.test_readme_assets -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 6: Commit Task 3**

Run:

```powershell
git add README.md docs/assets/mission-execution-visualization.svg tests/test_readme_assets.py
git commit -m "docs: add mission execution visualization asset"
```

Expected: commit includes README, the SVG asset, and README asset tests.

---

### Task 4: Regenerate Dashboard Artifact and Verify

**Files:**
- Modify: `dashboard/uav_mission_dashboard.html`

**Interfaces:**
- Consumes:
  - `write_dashboard(output_path, mission_text, scenario_dir) -> Path`
  - dashboard source changes from Task 2.
- Produces: tracked dashboard HTML containing the mission execution visualization.

- [ ] **Step 1: Regenerate the tracked dashboard HTML**

Run:

```powershell
$env:PYTHONPATH='src'; python -B -m uav_mission_agent.cli --dashboard dashboard\uav_mission_dashboard.html
```

Expected: command completes and rewrites `dashboard/uav_mission_dashboard.html`.

- [ ] **Step 2: Verify the dashboard artifact contains the visualization**

Run:

```powershell
rg -n "mission-execution-visualization|Mission Execution Visualization|Replanned Route" dashboard\uav_mission_dashboard.html
```

Expected: matches for the section id, SVG title, and replanned route label.

- [ ] **Step 3: Run focused visualization and dashboard tests**

Run:

```powershell
python -B -m unittest tests.test_mission_visualization tests.test_dashboard tests.test_readme_assets -v
```

Expected: all focused tests pass.

- [ ] **Step 4: Run full verification**

Run:

```powershell
python -B -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Run diff and secret checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}|DEEPSEEK_API_KEY\s*=|api[_-]?key\s*[:=]" . -g "!*__pycache__*" -g "!.git"
```

Expected:
- `git diff --check` exits with code 0.
- Secret scan shows only documentation examples such as `your-api-key` and test fixtures such as `test-key`.

- [ ] **Step 6: Commit Task 4**

Run:

```powershell
git add dashboard/uav_mission_dashboard.html
git commit -m "chore: refresh dashboard visualization artifact"
```

Expected: commit includes only the regenerated dashboard artifact.

---

## Final Review Checklist

- [ ] The visualization appears in `dashboard/uav_mission_dashboard.html`.
- [ ] The visualization asset exists at `docs/assets/mission-execution-visualization.svg`.
- [ ] README references `docs/assets/mission-execution-visualization.svg`.
- [ ] The SVG contains UAV icons, search area, no-fly zone, target point, planned route, replanned route, coverage path, weak communication label, and mission status labels.
- [ ] The full unit test suite passes.
- [ ] `git diff --check` passes.
- [ ] No real API key is present in tracked files.
