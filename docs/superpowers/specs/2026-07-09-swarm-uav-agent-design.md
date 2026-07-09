# Swarm UAV Agent Stage 1 Design

## Objective

Establish the data foundation for a multi-UAV swarm prototype. The project should model each UAV as an independent agent with role, position, battery state, communication quality, assigned objective, and references to swarm memory events.

## Scope

- Add a focused swarm data model module for grid positions, UAV states, events, detected targets, in-memory swarm memory, and mission-level swarm state.
- Keep default execution offline and dependency-free.
- Use standard-library dataclasses and explicit `to_dict()` methods, matching the existing `models.py` style.
- Support JSON-friendly serialization for UAV states, targets, events, memory, and mission state.
- Support simple in-memory retrieval by UAV id, event type, target id, area id, and risk keyword.
- Record failure experiences as first-class swarm events.

## Non-Goals

- Do not add vector database persistence in this stage.
- Do not integrate the new swarm model into FastAPI, CLI, dashboard, or benchmark flows yet.
- Do not add real flight-control APIs, physics simulation, GIS tiles, or live LLM calls.
- Do not require DeepSeek, OpenAI-compatible providers, FAISS, Chroma, or network access.
- Do not change public README positioning toward job-search language.

## Architecture

The first stage adds `src/uav_mission_agent/swarm_models.py` as a standalone model layer. Later swarm environment, algorithm, coordinator, dialogue, and demo modules will consume these objects without needing to know how memory stores events.

The model layer is deliberately small:

- `GridPosition` stores integer grid coordinates and serializes to `{ "x": int, "y": int }`.
- `UAVAgentState` stores per-UAV identity, role, position, battery, objective, status, communication quality, assigned area, and memory references.
- `SwarmEvent` stores timestamped operational events with optional UAV, target, area, severity, and metadata.
- `DetectedTarget` stores target observations with type, position, confidence, discovering UAV, timestamp, and handling status.
- `SwarmMemory` keeps in-memory event and target lists and provides simple retrieval helpers.
- `SwarmMissionState` groups mission id, agents, memory, base position, optional grid size, and current phase.

## Event Model

Events are stored as plain records so they can be displayed in CLI, JSON, and future UI timelines. Event types are intentionally string-based for now to keep the model extensible while the swarm coordinator design evolves.

Recommended event type values for Stage 1 tests:

- `mission_started`
- `area_assigned`
- `target_detected`
- `battery_warning`
- `communication_degraded`
- `replanning`
- `mission_completed`
- `failure_experience`

Failure experiences use `event_type="failure_experience"` and include structured metadata such as `reason`, `impact`, and `recommended_action`.

## Serialization

All model objects expose `to_dict()` and return JSON-friendly dictionaries. Nested model objects are recursively converted to dictionaries, and lists are copied so callers cannot mutate internal collections through serialized output.

`SwarmMemory.to_dict()` returns:

```python
{
    "events": [...],
    "targets": [...],
}
```

`SwarmMissionState.to_dict()` returns:

```python
{
    "mission_id": "...",
    "phase": "...",
    "base_position": {"x": 0, "y": 0},
    "grid_size": {"width": 20, "height": 20},
    "agents": [...],
    "memory": {...},
}
```

## Retrieval

`SwarmMemory` provides deterministic list-based retrieval:

- `events_for_uav(uav_id: str) -> list[SwarmEvent]`
- `events_by_type(event_type: str) -> list[SwarmEvent]`
- `targets_by_type(target_type: str) -> list[DetectedTarget]`
- `events_for_area(area_id: str) -> list[SwarmEvent]`
- `search_events(keyword: str) -> list[SwarmEvent]`

Search checks event type, message, severity, UAV id, target id, area id, and metadata values case-insensitively.

## Error Handling

Stage 1 keeps validation lightweight:

- `UAVAgentState.__post_init__()` rejects battery levels outside `0..100`.
- `UAVAgentState.__post_init__()` rejects communication quality outside `0..1`.
- `DetectedTarget.__post_init__()` rejects confidence outside `0..1`.

The model layer does not raise for unknown role, status, or event type strings yet; coordinator and algorithm layers can introduce stricter domain validation later.

## Testing Strategy

Unit tests cover:

- Creating and serializing independent UAV agent states.
- Creating a mission state with multiple agents and memory.
- Adding and retrieving events by UAV id, event type, area, and keyword.
- Recording detected targets and retrieving them by type.
- Recording failure experiences with structured metadata.
- Rejecting invalid battery, communication quality, and target confidence values.

## Acceptance Criteria

- `tests/test_swarm_models.py` passes.
- Full test suite remains offline and green.
- The new model layer uses only the Python standard library.
- The project now models each UAV as an independent agent with role, position, battery, communication state, assigned objective, and swarm memory events.
