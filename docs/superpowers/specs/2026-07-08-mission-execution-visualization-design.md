# Mission Execution Visualization Design

## Objective

Add a UAV mission execution visualization that helps viewers understand how the agent output maps to an operational scene: UAVs, search area, no-fly zone, target point, communication condition, route replanning, and mission status.

## Recommended Approach

Build a static SVG-based mission map and render it in two places:

- the local HTML dashboard as a new `Mission Execution Visualization` section;
- a reusable README asset under `docs/assets/`.

This keeps the project offline, dependency-light, and easy to inspect on GitHub while still showing a concrete UAV task execution scene.

## Scope

- Generate a deterministic 2D mission scene from the current mission plan/config.
- Show these visual elements:
  - operating boundary and grid;
  - search area;
  - no-fly zone;
  - target point;
  - two or three UAV icons depending on parsed UAV count;
  - planned route, replanned route, and observed coverage path;
  - weak-communication indicator when the mission has low-bandwidth coordination;
  - mission progress/status labels.
- Embed the SVG in `dashboard/uav_mission_dashboard.html`.
- Add a static SVG preview asset for README.
- Add focused tests for the renderer and dashboard integration.

## Non-Goals

- Do not build a simulation engine or physics model.
- Do not add a heavy JavaScript framework.
- Do not require live LLM/API keys for visualization.
- Do not animate the first version; keep GIF/animation as a later enhancement.

## Architecture

Add a small module, `mission_visualization.py`, with pure functions:

- build mission scene data from an agent plan;
- render that scene as inline SVG;
- write the SVG asset to disk.

The dashboard imports the renderer and embeds the resulting SVG. README references the generated static SVG asset.

## Data Flow

1. CLI/dashboard runs the existing agent workflow.
2. The workflow returns `mission_config`, task objectives, constraints, recommendations, and risks.
3. The visualization module maps that plan to a deterministic scene.
4. The dashboard renders the inline SVG section.
5. The same renderer writes `docs/assets/mission-execution-visualization.svg` for GitHub display.

## Testing

- Unit test that the SVG contains UAVs, search area, no-fly zone, target point, route, replanning route, and communication indicator.
- Dashboard test that the HTML contains the new visualization section.
- CLI or asset-generation smoke test if a command is added.
- Run the full unit test suite before completion.

## Acceptance Criteria

- `python -B -m unittest discover -s tests -v` passes.
- Dashboard HTML includes a mission execution visualization section.
- `docs/assets/mission-execution-visualization.svg` exists and is referenced by README.
- The visualization is deterministic and works offline.
