# Swarm UAV Agent Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Stage 1 swarm data model foundation for independent UAV agents and in-memory swarm events.

**Architecture:** Add a standalone `swarm_models.py` module that follows the repository's existing dataclass-plus-`to_dict()` pattern. Keep memory list-based and deterministic so later environment, algorithm, coordinator, and demo layers can consume the same objects without adding dependencies.

**Tech Stack:** Python 3.10+, standard library dataclasses, pytest/unittest-compatible tests, offline execution only.

## Global Constraints

- Keep default execution offline and dependency-free.
- Do not integrate the new swarm model into FastAPI, CLI, dashboard, benchmark, or live provider flows in this stage.
- Do not add vector database persistence in this stage.
- Do not require API keys, DeepSeek, OpenAI-compatible providers, FAISS, Chroma, or network access.
- Match the existing `models.py` style: dataclasses with explicit `to_dict()` methods.
- Public project positioning remains technical and project-oriented, not job-search-oriented.

---

### Task 1: Swarm Model Tests

**Files:**
- Create: `tests/test_swarm_models.py`
- Create later: `src/uav_mission_agent/swarm_models.py`

**Interfaces:**
- Produces test coverage for `GridPosition`, `UAVAgentState`, `SwarmEvent`, `DetectedTarget`, `SwarmMemory`, and `SwarmMissionState`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_swarm_models.py` with tests for:

```python
from uav_mission_agent.swarm_models import (
    DetectedTarget,
    GridPosition,
    SwarmEvent,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)


def test_uav_agent_state_serializes_independent_agent_fields():
    agent = UAVAgentState(
        uav_id="UAV-1",
        role="scout",
        position=GridPosition(3, 4),
        battery_level=87.5,
        assigned_area="mountain-a-north",
        current_objective="Search north ridge",
        status="active",
        communication_quality=0.92,
        memory_refs=["evt-001"],
    )

    assert agent.to_dict() == {
        "uav_id": "UAV-1",
        "role": "scout",
        "position": {"x": 3, "y": 4},
        "battery_level": 87.5,
        "assigned_area": "mountain-a-north",
        "current_objective": "Search north ridge",
        "status": "active",
        "communication_quality": 0.92,
        "memory_refs": ["evt-001"],
    }
```

- [ ] **Step 2: Verify red**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_models.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav`

Expected: FAIL with `ModuleNotFoundError: No module named 'uav_mission_agent.swarm_models'`.

- [ ] **Step 3: Add remaining failing tests**

Extend the same test file to cover memory event retrieval, target recording, failure experience recording, mission state serialization, and validation errors for invalid battery, communication quality, and target confidence.

- [ ] **Step 4: Verify red again**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_models.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav`

Expected: FAIL because the production module still does not exist.

### Task 2: Swarm Model Implementation

**Files:**
- Create: `src/uav_mission_agent/swarm_models.py`
- Test: `tests/test_swarm_models.py`

**Interfaces:**
- Produces: `GridPosition(x: int, y: int)`
- Produces: `UAVAgentState(uav_id: str, role: str, position: GridPosition, battery_level: float, assigned_area: str | None = None, current_objective: str | None = None, status: str = "idle", communication_quality: float = 1.0, memory_refs: list[str] | None = None)`
- Produces: `SwarmEvent(event_id: str, event_type: str, message: str, timestamp: str, uav_id: str | None = None, target_id: str | None = None, area_id: str | None = None, severity: str = "info", metadata: dict[str, Any] | None = None)`
- Produces: `DetectedTarget(target_id: str, target_type: str, position: GridPosition, confidence: float, detected_by: str, timestamp: str, status: str = "new", metadata: dict[str, Any] | None = None)`
- Produces: `SwarmMemory(events: list[SwarmEvent] | None = None, targets: list[DetectedTarget] | None = None)`
- Produces: `SwarmMissionState(mission_id: str, agents: list[UAVAgentState], memory: SwarmMemory, base_position: GridPosition, phase: str = "planning", grid_size: dict[str, int] | None = None)`

- [ ] **Step 1: Implement minimal dataclasses**

Create `src/uav_mission_agent/swarm_models.py` with dataclasses, validations, and `to_dict()` methods matching the tests.

- [ ] **Step 2: Implement memory helpers**

Add:

```python
def add_event(self, event: SwarmEvent) -> SwarmEvent: ...
def add_target(self, target: DetectedTarget) -> DetectedTarget: ...
def record_failure(self, event_id: str, message: str, timestamp: str, *, uav_id: str | None = None, area_id: str | None = None, reason: str | None = None, impact: str | None = None, recommended_action: str | None = None) -> SwarmEvent: ...
def events_for_uav(self, uav_id: str) -> list[SwarmEvent]: ...
def events_by_type(self, event_type: str) -> list[SwarmEvent]: ...
def events_for_area(self, area_id: str) -> list[SwarmEvent]: ...
def targets_by_type(self, target_type: str) -> list[DetectedTarget]: ...
def search_events(self, keyword: str) -> list[SwarmEvent]: ...
```

- [ ] **Step 3: Verify green for focused tests**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_swarm_models.py -q -o cache_dir=$env:TEMP\\pytest-cache-uav`

Expected: PASS.

### Task 3: Full Verification And Commit

**Files:**
- `docs/superpowers/specs/2026-07-09-swarm-uav-agent-design.md`
- `docs/superpowers/plans/2026-07-09-swarm-uav-agent.md`
- `src/uav_mission_agent/swarm_models.py`
- `tests/test_swarm_models.py`

**Interfaces:**
- Consumes all Stage 1 model interfaces from Task 2.
- Produces a committed Stage 1 baseline for later environment and coordinator work.

- [ ] **Step 1: Run full test suite**

Run: `$env:PYTHONPATH='src'; python -m pytest -o cache_dir=$env:TEMP\\pytest-cache-uav`

Expected: Existing suite plus new swarm model tests pass.

- [ ] **Step 2: Inspect git diff**

Run: `git diff -- docs/superpowers/specs/2026-07-09-swarm-uav-agent-design.md docs/superpowers/plans/2026-07-09-swarm-uav-agent.md src/uav_mission_agent/swarm_models.py tests/test_swarm_models.py`

Expected: Diff only contains Stage 1 docs, model code, and model tests.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-07-09-swarm-uav-agent-design.md docs/superpowers/plans/2026-07-09-swarm-uav-agent.md src/uav_mission_agent/swarm_models.py tests/test_swarm_models.py
git commit -m "feat: add swarm UAV data models"
```

Expected: Commit succeeds on branch `swarm-uav-agent-stage1`.
