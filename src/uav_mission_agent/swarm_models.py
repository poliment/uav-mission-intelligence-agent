from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass
class GridPosition:
    x: int
    y: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass
class UAVAgentState:
    uav_id: str
    role: str
    position: GridPosition
    battery_level: float
    assigned_area: str | None = None
    current_objective: str | None = None
    status: str = "idle"
    communication_quality: float = 1.0
    memory_refs: list[str] | None = None

    def __post_init__(self) -> None:
        _validate_range("battery_level", self.battery_level, 0.0, 100.0)
        _validate_range("communication_quality", self.communication_quality, 0.0, 1.0)
        self.memory_refs = list(self.memory_refs or [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "uav_id": self.uav_id,
            "role": self.role,
            "position": self.position.to_dict(),
            "battery_level": self.battery_level,
            "assigned_area": self.assigned_area,
            "current_objective": self.current_objective,
            "status": self.status,
            "communication_quality": self.communication_quality,
            "memory_refs": list(self.memory_refs or []),
        }


@dataclass
class SwarmEvent:
    event_id: str
    event_type: str
    message: str
    timestamp: str
    uav_id: str | None = None
    target_id: str | None = None
    area_id: str | None = None
    severity: str = "info"
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.metadata = deepcopy(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp,
            "uav_id": self.uav_id,
            "target_id": self.target_id,
            "area_id": self.area_id,
            "severity": self.severity,
            "metadata": deepcopy(self.metadata or {}),
        }


@dataclass
class DetectedTarget:
    target_id: str
    target_type: str
    position: GridPosition
    confidence: float
    detected_by: str
    timestamp: str
    status: str = "new"
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        _validate_range("confidence", self.confidence, 0.0, 1.0)
        self.metadata = deepcopy(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "position": self.position.to_dict(),
            "confidence": self.confidence,
            "detected_by": self.detected_by,
            "timestamp": self.timestamp,
            "status": self.status,
            "metadata": deepcopy(self.metadata or {}),
        }


@dataclass
class SwarmMemory:
    events: list[SwarmEvent] | None = None
    targets: list[DetectedTarget] | None = None

    def __post_init__(self) -> None:
        self.events = list(self.events or [])
        self.targets = list(self.targets or [])

    def add_event(self, event: SwarmEvent) -> SwarmEvent:
        self.events.append(event)
        return event

    def add_target(self, target: DetectedTarget) -> DetectedTarget:
        self.targets.append(target)
        return target

    def record_failure(
        self,
        event_id: str,
        message: str,
        timestamp: str,
        *,
        uav_id: str | None = None,
        area_id: str | None = None,
        reason: str | None = None,
        impact: str | None = None,
        recommended_action: str | None = None,
    ) -> SwarmEvent:
        metadata = {
            key: value
            for key, value in {
                "reason": reason,
                "impact": impact,
                "recommended_action": recommended_action,
            }.items()
            if value is not None
        }
        return self.add_event(
            SwarmEvent(
                event_id=event_id,
                event_type="failure_experience",
                message=message,
                timestamp=timestamp,
                uav_id=uav_id,
                area_id=area_id,
                severity="warning",
                metadata=metadata,
            )
        )

    def events_for_uav(self, uav_id: str) -> list[SwarmEvent]:
        return [event for event in self.events or [] if event.uav_id == uav_id]

    def events_by_type(self, event_type: str) -> list[SwarmEvent]:
        return [
            event
            for event in self.events or []
            if event.event_type.lower() == event_type.lower()
        ]

    def events_for_area(self, area_id: str) -> list[SwarmEvent]:
        return [event for event in self.events or [] if event.area_id == area_id]

    def targets_by_type(self, target_type: str) -> list[DetectedTarget]:
        return [
            target
            for target in self.targets or []
            if target.target_type.lower() == target_type.lower()
        ]

    def search_events(self, keyword: str) -> list[SwarmEvent]:
        normalized_keyword = keyword.lower()
        if not normalized_keyword:
            return []
        return [
            event
            for event in self.events or []
            if normalized_keyword in _event_search_text(event)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [event.to_dict() for event in self.events or []],
            "targets": [target.to_dict() for target in self.targets or []],
        }


@dataclass
class SwarmMissionState:
    mission_id: str
    agents: list[UAVAgentState]
    memory: SwarmMemory
    base_position: GridPosition
    phase: str = "planning"
    grid_size: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "phase": self.phase,
            "base_position": self.base_position.to_dict(),
            "grid_size": dict(self.grid_size) if self.grid_size is not None else None,
            "agents": [agent.to_dict() for agent in self.agents],
            "memory": self.memory.to_dict(),
        }


def _validate_range(name: str, value: float, minimum: float, maximum: float) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def _event_search_text(event: SwarmEvent) -> str:
    parts = [
        event.event_id,
        event.event_type,
        event.message,
        event.uav_id,
        event.target_id,
        event.area_id,
        event.severity,
        *_metadata_values(event.metadata or {}),
    ]
    return " ".join(str(part).lower() for part in parts if part is not None)


def _metadata_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key, value in metadata.items():
        values.append(str(key))
        if isinstance(value, dict):
            values.extend(_metadata_values(value))
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
        else:
            values.append(str(value))
    return values
