# Swarm Environment Stage 2 Design

## Objective

Add a deterministic two-dimensional virtual environment for the swarm UAV prototype. The environment should let UAV agents move on a grid, consume battery, evaluate communication quality, discover targets, and write operational events into swarm memory.

## Scope

- Add `src/uav_mission_agent/swarm_environment.py`.
- Add `tests/test_swarm_environment.py`.
- Reuse Stage 1 models from `swarm_models.py`.
- Support bounded grid maps with base position, communication center, communication range, obstacles, no-fly zones, and scenario targets.
- Provide Manhattan and Euclidean distance helpers.
- Move one UAV one grid step toward an objective with deterministic axis preference and blocked-cell fallback.
- Execute one deterministic tick over a `SwarmMissionState`.
- Record low battery, target detected, communication degraded, and movement blocked events into `SwarmMemory`.
- Keep default execution offline and dependency-free.

## Non-Goals

- Do not integrate the environment into FastAPI, CLI, dashboard, benchmark, or README in this stage.
- Do not add physics simulation, continuous flight dynamics, path planners, GIS tiles, or real flight-control APIs.
- Do not call live LLM providers.
- Do not add third-party dependencies.
- Do not push to GitHub until Stage 2 is merged into local `main` and verified.

## Architecture

The environment layer is a focused deterministic module above the Stage 1 model layer:

```text
SwarmMissionState
        |
        v
SwarmGridEnvironment.tick(...)
        |
        +--> movement and battery update
        +--> communication quality update
        +--> target discovery
        +--> event creation
        |
        v
SwarmEnvironmentTick + updated SwarmMemory
```

`SwarmGridEnvironment` owns static scenario geometry and simple rules. It does not own mission planning policy; callers provide per-UAV objectives as `dict[str, GridPosition]`.

## Core Interfaces

`SwarmGridEnvironment`:

- `in_bounds(position: GridPosition) -> bool`
- `is_obstacle(position: GridPosition) -> bool`
- `is_no_fly_zone(position: GridPosition) -> bool`
- `is_blocked(position: GridPosition) -> bool`
- `manhattan_distance(start: GridPosition, end: GridPosition) -> int`
- `euclidean_distance(start: GridPosition, end: GridPosition) -> float`
- `communication_quality_at(position: GridPosition) -> float`
- `is_in_communication_range(position: GridPosition) -> bool`
- `next_step_toward(start: GridPosition, destination: GridPosition) -> GridPosition`
- `move_agent_toward(agent: UAVAgentState, destination: GridPosition) -> UAVAgentState`
- `tick(mission_state: SwarmMissionState, objectives: dict[str, GridPosition], timestamp: str) -> SwarmEnvironmentTick`

`SwarmEnvironmentTick`:

- `agents: list[UAVAgentState]`
- `events: list[SwarmEvent]`
- `detected_targets: list[DetectedTarget]`
- `to_dict() -> dict[str, Any]`

## Movement Rules

Movement is intentionally simple and reproducible:

- A UAV moves at most one grid cell per tick.
- Horizontal movement is preferred when both axes differ.
- If the preferred cell is blocked, the environment tries the other axis.
- Blocked means out of bounds, obstacle, or no-fly zone.
- If no valid candidate exists, the UAV stays in place and receives a `movement_blocked` event.
- Battery decreases by `battery_drain_per_step` only when position changes.

This is enough for demos and tests without pretending to be a real path planner.

## Event Rules

`tick()` writes events to the mission state's `SwarmMemory`:

- `battery_warning`: updated battery is at or below `low_battery_threshold`.
- `communication_degraded`: updated communication quality is below `degraded_communication_threshold`.
- `target_detected`: a scenario target is within `discovery_range` of a UAV and is not already in memory.
- `movement_blocked`: a UAV has an objective but no safe one-step move exists.

Event ids are deterministic and include timestamp, UAV id, and event type so demo output is reproducible.

## Serialization

`SwarmGridEnvironment.to_dict()` returns JSON-friendly environment geometry:

```python
{
    "width": 20,
    "height": 20,
    "base_position": {"x": 0, "y": 0},
    "communication_center": {"x": 0, "y": 0},
    "communication_range": 8.0,
    "obstacles": [{"x": 5, "y": 5}],
    "no_fly_zones": [{"x": 6, "y": 5}],
    "targets": [...],
}
```

`SwarmEnvironmentTick.to_dict()` returns updated agents, events, and detected targets.

## Testing Strategy

Unit tests cover:

- Environment serialization for grid features and targets.
- Manhattan and Euclidean distances plus communication range/quality checks.
- One-step movement with battery consumption and blocked-cell fallback.
- Tick-generated low battery, target detection, and communication degradation events.
- Movement blocked events when all one-step options are unsafe.

## Acceptance Criteria

- `tests/test_swarm_environment.py` passes after a red-green TDD cycle.
- Full test suite passes offline.
- The environment layer uses only the Python standard library.
- Stage 2 is merged into local `main` after verification.
- Local `main` is pushed to GitHub only after Stage 2 is verified.
