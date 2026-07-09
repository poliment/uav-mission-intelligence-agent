# Swarm Algorithms Stage 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an A*-based traditional algorithm layer for swarm pathfinding, feasibility checks, candidate scoring, and target assignment, then reshape README into a coherent public project overview.

**Architecture:** Implement `swarm_algorithms.py` as a standalone deterministic tool layer above `swarm_environment.py` and `swarm_models.py`. A* supplies obstacle-aware path distance, while battery, communication, scoring, and assignment utilities produce explainable JSON-friendly outputs.

**Tech Stack:** Python 3.10+, standard library `dataclasses`/`heapq`, existing swarm dataclasses, pytest/unittest-compatible tests, offline execution only.

## Global Constraints

- Use A* as the core pathfinding and path-distance algorithm.
- Reuse Stage 1 swarm models and Stage 2 grid environment.
- Keep default execution offline and dependency-free.
- Do not integrate the algorithm layer into the coordinator, FastAPI demo, benchmark, or CLI in this stage.
- Do not add third-party path-planning packages.
- README must read like a public project overview and must not use job-search-oriented wording.

---

### Task 1: A* Algorithm Tests

**Files:**
- Create: `tests/test_swarm_algorithms.py`
- Create later: `src/uav_mission_agent/swarm_algorithms.py`

**Interfaces:**
- Produces tests for `astar_path`, feasibility checks, candidate scoring, and target assignment.
- Consumes `GridPosition`, `UAVAgentState`, `DetectedTarget`, and `SwarmGridEnvironment`.

- [ ] **Step 1: Write failing tests**

Create tests that assert:

- A* avoids blocked cells and returns a shortest reachable path.
- A* returns `reachable=False` when start is boxed in.
- Battery feasibility uses A* path distance plus reserve battery.
- Communication coverage lists weak path points.
- Candidate scoring prefers closer feasible UAVs.
- Assignment records are serializable and explain why a target was assigned.

- [ ] **Step 2: Verify red**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_algorithms.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav-stage3`

Expected: FAIL with `ModuleNotFoundError: No module named 'uav_mission_agent.swarm_algorithms'`.

### Task 2: A* Algorithm Implementation

**Files:**
- Create: `src/uav_mission_agent/swarm_algorithms.py`
- Test: `tests/test_swarm_algorithms.py`

**Interfaces:**
- Produces: `AStarPathResult`
- Produces: `ConstraintCheck`
- Produces: `CandidateScore`
- Produces: `TargetAssignment`
- Produces: `astar_path(...)`
- Produces: `check_battery_feasibility(...)`
- Produces: `check_communication_coverage(...)`
- Produces: `score_candidate_for_target(...)`
- Produces: `assign_targets_to_uavs(...)`

- [ ] **Step 1: Implement A* and result serialization**

Use four-neighbor grid movement, Manhattan heuristic, and environment `is_blocked()` checks.

- [ ] **Step 2: Implement feasibility and communication checks**

Battery check should use `path.distance * battery_per_step + reserve_battery`. Communication check should inspect every path point with `environment.communication_quality_at()`.

- [ ] **Step 3: Implement scoring and assignment**

Candidate scores should be deterministic and explainable. Target assignment should greedily choose the best unused feasible UAV for each target, falling back to the highest-scoring candidate when all checks fail.

- [ ] **Step 4: Verify green**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_algorithms.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav-stage3`

Expected: PASS.

### Task 3: README Project Overview

**Files:**
- Modify: `README.md`
- Modify: `tests/test_readme_assets.py`

**Interfaces:**
- README must include the existing required demo/RAG strings.
- README must document A* swarm algorithm tools.

- [ ] **Step 1: Write failing README assertion**

Add assertions that README contains `A* path planning`, `swarm_algorithms.py`, and `Swarm upgrade status`.

- [ ] **Step 2: Verify red**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_readme_assets.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav-stage3`

Expected: FAIL before README is rewritten.

- [ ] **Step 3: Rewrite README**

Restructure README as a public project overview with sections for overview, capabilities, architecture, quick start, interactive demo, tests, and project structure.

- [ ] **Step 4: Verify README tests**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_readme_assets.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav-stage3`

Expected: PASS.

### Task 4: Full Verification And Merge

**Files:**
- `docs/superpowers/specs/2026-07-09-swarm-algorithms-design.md`
- `docs/superpowers/plans/2026-07-09-swarm-algorithms.md`
- `src/uav_mission_agent/swarm_algorithms.py`
- `tests/test_swarm_algorithms.py`
- `tests/test_readme_assets.py`
- `README.md`

**Interfaces:**
- Consumes all Stage 3 interfaces from earlier tasks.
- Produces a local `main` branch containing Stage 3.

- [ ] **Step 1: Run full tests in the Stage 3 worktree**

Run: `$env:PYTHONPATH='src'; python -m pytest -o cache_dir=$env:TEMP\\pytest-cache-uav-stage3`

Expected: Full suite passes.

- [ ] **Step 2: Commit Stage 3**

Run:

```bash
git add docs/superpowers/specs/2026-07-09-swarm-algorithms-design.md docs/superpowers/plans/2026-07-09-swarm-algorithms.md src/uav_mission_agent/swarm_algorithms.py tests/test_swarm_algorithms.py tests/test_readme_assets.py README.md
git commit -m "feat: add A-star swarm algorithms"
```

Expected: Commit succeeds on branch `swarm-uav-agent-stage3`.

- [ ] **Step 3: Merge into local main and verify**

Run from the main checkout:

```bash
git pull --ff-only
git merge swarm-uav-agent-stage3
$env:PYTHONPATH='src'; python -m pytest -o cache_dir=$env:TEMP\\pytest-cache-uav-stage3-main
```

Expected: Merge succeeds and tests pass on `main`.
