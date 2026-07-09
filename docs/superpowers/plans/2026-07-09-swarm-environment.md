# Swarm Environment Stage 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic two-dimensional virtual environment that can move UAV agents, consume battery, check communication, discover targets, and write swarm events.

**Architecture:** Add `swarm_environment.py` as a standalone rules layer above `swarm_models.py`. The module owns static grid geometry and tick mechanics, while callers provide mission state and per-UAV objectives.

**Tech Stack:** Python 3.10+, standard library dataclasses/math/copy, pytest/unittest-compatible tests, offline execution only.

## Global Constraints

- Keep default execution offline and dependency-free.
- Reuse Stage 1 models from `src/uav_mission_agent/swarm_models.py`.
- Do not integrate the environment into FastAPI, CLI, dashboard, benchmark, or README in this stage.
- Do not add physics simulation, continuous flight dynamics, path planners, GIS tiles, or real flight-control APIs.
- Do not call live LLM providers.
- Push to GitHub only after Stage 2 is merged into local `main` and verified.

---

### Task 1: Environment Tests

**Files:**
- Create: `tests/test_swarm_environment.py`
- Create later: `src/uav_mission_agent/swarm_environment.py`

**Interfaces:**
- Produces tests for `SwarmGridEnvironment` and `SwarmEnvironmentTick`.
- Consumes `GridPosition`, `UAVAgentState`, `DetectedTarget`, `SwarmMemory`, and `SwarmMissionState`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_swarm_environment.py` with tests for environment serialization, distance helpers, communication quality, movement, tick events, and blocked movement.

- [ ] **Step 2: Verify red**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_environment.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav-stage2`

Expected: FAIL with `ModuleNotFoundError: No module named 'uav_mission_agent.swarm_environment'`.

### Task 2: Environment Implementation

**Files:**
- Create: `src/uav_mission_agent/swarm_environment.py`
- Test: `tests/test_swarm_environment.py`

**Interfaces:**
- Produces: `SwarmGridEnvironment(width: int, height: int, base_position: GridPosition, communication_center: GridPosition | None = None, communication_range: float = 8.0, obstacles: list[GridPosition] | None = None, no_fly_zones: list[GridPosition] | None = None, targets: list[DetectedTarget] | None = None, battery_drain_per_step: float = 1.0, low_battery_threshold: float = 25.0, degraded_communication_threshold: float = 0.35, discovery_range: int = 0)`
- Produces: `SwarmEnvironmentTick(agents: list[UAVAgentState], events: list[SwarmEvent], detected_targets: list[DetectedTarget])`
- Produces: `tick(mission_state: SwarmMissionState, objectives: dict[str, GridPosition], timestamp: str) -> SwarmEnvironmentTick`

- [ ] **Step 1: Implement geometry and serialization**

Add grid validation, position checks, obstacle/no-fly checks, distance helpers, communication helpers, and `to_dict()`.

- [ ] **Step 2: Implement movement**

Add `next_step_toward()` and `move_agent_toward()` with deterministic horizontal-first one-step movement, blocked-cell fallback, and battery drain only when the position changes.

- [ ] **Step 3: Implement tick events**

Add `tick()` to update mission agents, write events to memory, discover targets, and return `SwarmEnvironmentTick`.

- [ ] **Step 4: Verify green**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_environment.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav-stage2`

Expected: PASS.

### Task 3: Full Verification, Merge, And Push

**Files:**
- `docs/superpowers/specs/2026-07-09-swarm-environment-design.md`
- `docs/superpowers/plans/2026-07-09-swarm-environment.md`
- `src/uav_mission_agent/swarm_environment.py`
- `tests/test_swarm_environment.py`

**Interfaces:**
- Consumes all Stage 2 environment interfaces from Task 2.
- Produces a committed Stage 2 branch that can be merged into `main`.

- [ ] **Step 1: Run full tests in the Stage 2 worktree**

Run: `$env:PYTHONPATH='src'; python -m pytest -o cache_dir=$env:TEMP\\pytest-cache-uav-stage2`

Expected: Existing suite plus new environment tests pass.

- [ ] **Step 2: Commit Stage 2**

Run:

```bash
git add docs/superpowers/specs/2026-07-09-swarm-environment-design.md docs/superpowers/plans/2026-07-09-swarm-environment.md src/uav_mission_agent/swarm_environment.py tests/test_swarm_environment.py
git commit -m "feat: add swarm grid environment"
```

Expected: Commit succeeds on branch `swarm-uav-agent-stage2`.

- [ ] **Step 3: Merge into local main and verify**

Run from the main checkout:

```bash
git checkout main
git merge swarm-uav-agent-stage2
$env:PYTHONPATH='src'; python -m pytest -o cache_dir=$env:TEMP\\pytest-cache-uav-stage2
```

Expected: Merge succeeds and tests pass on `main`.

- [ ] **Step 4: Push main to GitHub**

Run: `git push origin main`

Expected: `origin/main` receives Stage 1 and Stage 2 commits.
