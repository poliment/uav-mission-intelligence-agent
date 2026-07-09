# Swarm Algorithms Stage 3 Design

## Objective

Add a deterministic traditional-algorithm layer for the swarm UAV prototype. This layer should use A* pathfinding as the core path and distance estimator, then expose explainable checks for battery feasibility, communication coverage, candidate scoring, and target assignment.

## Scope

- Add `src/uav_mission_agent/swarm_algorithms.py`.
- Add `tests/test_swarm_algorithms.py`.
- Use Stage 1 swarm models and Stage 2 grid environment.
- Implement A* over four-neighbor grid movement.
- Respect environment boundaries, obstacles, and no-fly zones.
- Return JSON-friendly, explainable result objects.
- Add README coverage that presents the repository as a coherent public project overview.

## Non-Goals

- Do not integrate the algorithm layer into the coordinator, FastAPI demo, benchmark, or CLI in this stage.
- Do not implement continuous-space planning, kinodynamic constraints, terrain costs, or multi-objective optimization.
- Do not add third-party path-planning packages.
- Do not call external LLM providers.
- Do not replace the Stage 2 tick movement rules yet; A* is exposed as a reusable tool layer for later coordinator/demo integration.

## Architecture

The Stage 3 layer sits between future swarm coordination and the Stage 2 environment:

```text
Swarm Coordinator / future demo
        |
        v
swarm_algorithms.py
        |
        +--> A* pathfinding
        +--> battery feasibility
        +--> communication coverage
        +--> candidate scoring
        +--> greedy target assignment
        |
        v
SwarmGridEnvironment + Swarm Models
```

The layer is deterministic and explainable. It does not decide mission intent; it validates and scores candidate actions that the coordinator can later reference.

## Core Interfaces

`AStarPathResult`:

- `start: GridPosition`
- `goal: GridPosition`
- `path: list[GridPosition]`
- `distance: int | None`
- `reachable: bool`
- `reason: str`
- `explored_nodes: int`

`ConstraintCheck`:

- `name: str`
- `passed: bool`
- `details: dict[str, Any]`

`CandidateScore`:

- `uav_id: str`
- `target_id: str`
- `score: float`
- `path: AStarPathResult`
- `battery_check: ConstraintCheck`
- `communication_check: ConstraintCheck`
- `explanation: str`

`TargetAssignment`:

- `target_id: str`
- `uav_id: str | None`
- `score: float`
- `path: AStarPathResult | None`
- `reason: str`

Functions:

- `astar_path(environment: SwarmGridEnvironment, start: GridPosition, goal: GridPosition) -> AStarPathResult`
- `check_battery_feasibility(agent: UAVAgentState, path: AStarPathResult, battery_per_step: float, reserve_battery: float = 10.0) -> ConstraintCheck`
- `check_communication_coverage(environment: SwarmGridEnvironment, path: AStarPathResult, min_quality: float = 0.35) -> ConstraintCheck`
- `score_candidate_for_target(agent: UAVAgentState, target: DetectedTarget, environment: SwarmGridEnvironment, *, battery_per_step: float | None = None, reserve_battery: float = 10.0, min_comm_quality: float = 0.35) -> CandidateScore`
- `assign_targets_to_uavs(agents: list[UAVAgentState], targets: list[DetectedTarget], environment: SwarmGridEnvironment, *, battery_per_step: float | None = None, reserve_battery: float = 10.0, min_comm_quality: float = 0.35) -> list[TargetAssignment]`

## A* Rules

- Movement uses four neighbors: right, down, left, up.
- Step cost is `1` per grid cell.
- The heuristic is Manhattan distance.
- A node is traversable when `environment.is_blocked(position)` is false.
- Start and goal must be in bounds and not blocked.
- If no path is found, the result is `reachable=False`, `path=[]`, and `distance=None`.
- Tie-breaking is deterministic by `f_score`, `h_score`, then coordinates.

## Scoring

Candidate scoring is intentionally simple:

- Unreachable path starts at `0`.
- Reachable candidates start from `100`.
- Path distance subtracts `distance * 5`.
- Failed battery check subtracts `35`.
- Failed communication check subtracts `20`.
- `relay` role gets a small communication-support bonus for covered paths.
- Scores are clamped at `0` and rounded to three decimals.

This produces explainable ranking without pretending to be a full optimizer.

## README Update

The README should read like a public project overview:

- Project purpose in the first screen.
- Current capabilities grouped by subsystem.
- Swarm upgrade status: models, environment, A* algorithm tools.
- Offline-first architecture and optional provider/RAG/demo extras.
- Quick start, example commands, testing, and repository structure.
- No job-search-oriented wording.

Existing test-required phrases and links must remain:

- `docs/assets/mission-execution-visualization.svg`
- `local vector RAG`
- `rag-faiss`
- `rag-chroma`
- `Interactive Demo / 交互式 Demo`
- `pip install -e ".[demo]"`
- `uav-mission-agent-demo --host 127.0.0.1 --port 8000`
- `uav-mission-agent-demo --env-file D:\epacode\working\.secrets\deepseek.env`
- `Agent trace`
- `provider comparison`

## Testing Strategy

Unit tests cover:

- A* finds shortest paths that avoid obstacles and no-fly zones.
- A* reports unreachable goals clearly.
- Battery feasibility uses A* path distance and reserve battery.
- Communication coverage reports weak path points.
- Candidate scoring prefers reachable, feasible, closer UAVs.
- Greedy target assignment returns explainable assignment records.
- README documents the A* swarm algorithm layer while retaining existing public-project requirements.

## Acceptance Criteria

- `tests/test_swarm_algorithms.py` passes after a red-green TDD cycle.
- README tests pass.
- Full test suite passes offline.
- Stage 3 is merged into local `main`.
