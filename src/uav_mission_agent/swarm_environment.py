from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any

from .swarm_models import (
    DetectedTarget,
    GridPosition,
    SwarmEvent,
    SwarmMissionState,
    UAVAgentState,
)


@dataclass
class SwarmEnvironmentTick:
    agents: list[UAVAgentState]
    events: list[SwarmEvent]
    detected_targets: list[DetectedTarget]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agents": [agent.to_dict() for agent in self.agents],
            "events": [event.to_dict() for event in self.events],
            "detected_targets": [target.to_dict() for target in self.detected_targets],
        }


@dataclass
class SwarmGridEnvironment:
    width: int
    height: int
    base_position: GridPosition
    communication_center: GridPosition | None = None
    communication_range: float = 8.0
    obstacles: list[GridPosition] | None = None
    no_fly_zones: list[GridPosition] | None = None
    targets: list[DetectedTarget] | None = None
    battery_drain_per_step: float = 1.0
    low_battery_threshold: float = 25.0
    degraded_communication_threshold: float = 0.35
    discovery_range: int = 0

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("environment width and height must be positive")
        if self.communication_range < 0:
            raise ValueError("communication_range must be non-negative")
        if self.battery_drain_per_step < 0:
            raise ValueError("battery_drain_per_step must be non-negative")
        if self.discovery_range < 0:
            raise ValueError("discovery_range must be non-negative")
        self.communication_center = self.communication_center or self.base_position
        self.obstacles = list(self.obstacles or [])
        self.no_fly_zones = list(self.no_fly_zones or [])
        self.targets = list(self.targets or [])
        self._obstacle_cells = {_position_key(position) for position in self.obstacles}
        self._no_fly_cells = {_position_key(position) for position in self.no_fly_zones}

    def in_bounds(self, position: GridPosition) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height

    def is_obstacle(self, position: GridPosition) -> bool:
        return _position_key(position) in self._obstacle_cells

    def is_no_fly_zone(self, position: GridPosition) -> bool:
        return _position_key(position) in self._no_fly_cells

    def is_blocked(self, position: GridPosition) -> bool:
        return (
            not self.in_bounds(position)
            or self.is_obstacle(position)
            or self.is_no_fly_zone(position)
        )

    def manhattan_distance(self, start: GridPosition, end: GridPosition) -> int:
        return abs(start.x - end.x) + abs(start.y - end.y)

    def euclidean_distance(self, start: GridPosition, end: GridPosition) -> float:
        return round(math.hypot(start.x - end.x, start.y - end.y), 3)

    def communication_quality_at(self, position: GridPosition) -> float:
        distance = self.euclidean_distance(self.communication_center, position)
        if self.communication_range == 0:
            return 1.0 if distance == 0 else 0.0
        if distance > self.communication_range:
            return 0.0
        return round(max(0.0, 1.0 - (distance / self.communication_range)), 3)

    def is_in_communication_range(self, position: GridPosition) -> bool:
        return self.euclidean_distance(self.communication_center, position) <= self.communication_range

    def next_step_toward(self, start: GridPosition, destination: GridPosition) -> GridPosition:
        if start.x == destination.x and start.y == destination.y:
            return GridPosition(start.x, start.y)

        candidates: list[GridPosition] = []
        dx = _step_delta(start.x, destination.x)
        dy = _step_delta(start.y, destination.y)
        if dx:
            candidates.append(GridPosition(start.x + dx, start.y))
        if dy:
            candidates.append(GridPosition(start.x, start.y + dy))

        for candidate in candidates:
            if not self.is_blocked(candidate):
                return candidate
        return GridPosition(start.x, start.y)

    def move_agent_toward(self, agent: UAVAgentState, destination: GridPosition) -> UAVAgentState:
        next_position = self.next_step_toward(agent.position, destination)
        moved = _position_key(next_position) != _position_key(agent.position)
        next_battery = agent.battery_level
        if moved:
            next_battery = max(0.0, round(agent.battery_level - self.battery_drain_per_step, 3))
        return replace(
            agent,
            position=next_position,
            battery_level=next_battery,
            communication_quality=self.communication_quality_at(next_position),
        )

    def tick(
        self,
        mission_state: SwarmMissionState,
        objectives: dict[str, GridPosition],
        timestamp: str,
    ) -> SwarmEnvironmentTick:
        events: list[SwarmEvent] = []
        detected_targets: list[DetectedTarget] = []
        updated_agents: list[UAVAgentState] = []
        known_target_ids = {target.target_id for target in mission_state.memory.targets or []}

        for agent in mission_state.agents:
            destination = objectives.get(agent.uav_id)
            updated_agent = agent
            blocked = False
            if destination is not None:
                updated_agent = self.move_agent_toward(agent, destination)
                blocked = (
                    _position_key(updated_agent.position) == _position_key(agent.position)
                    and _position_key(agent.position) != _position_key(destination)
                )

            if blocked:
                updated_agent = replace(updated_agent, status="blocked")
                events.append(
                    self._event(
                        timestamp,
                        updated_agent.uav_id,
                        "movement_blocked",
                        f"{updated_agent.uav_id} could not move safely toward objective.",
                        severity="warning",
                        metadata={
                            "position": updated_agent.position.to_dict(),
                            "destination": destination.to_dict() if destination is not None else None,
                        },
                    )
                )
            else:
                if updated_agent.battery_level <= self.low_battery_threshold:
                    updated_agent = replace(
                        updated_agent,
                        status="returning",
                        current_objective="Return to base for recharge",
                    )
                    events.append(
                        self._event(
                            timestamp,
                            updated_agent.uav_id,
                            "battery_warning",
                            f"{updated_agent.uav_id} battery is below reserve threshold.",
                            severity="warning",
                            metadata={
                                "battery_level": updated_agent.battery_level,
                                "threshold": self.low_battery_threshold,
                            },
                        )
                    )

                if updated_agent.communication_quality < self.degraded_communication_threshold:
                    events.append(
                        self._event(
                            timestamp,
                            updated_agent.uav_id,
                            "communication_degraded",
                            f"{updated_agent.uav_id} communication quality degraded.",
                            severity="warning",
                            metadata={
                                "communication_quality": updated_agent.communication_quality,
                                "threshold": self.degraded_communication_threshold,
                            },
                        )
                    )

                for target in self.targets or []:
                    if target.target_id in known_target_ids:
                        continue
                    if self.manhattan_distance(updated_agent.position, target.position) <= self.discovery_range:
                        discovered = DetectedTarget(
                            target_id=target.target_id,
                            target_type=target.target_type,
                            position=GridPosition(target.position.x, target.position.y),
                            confidence=target.confidence,
                            detected_by=updated_agent.uav_id,
                            timestamp=timestamp,
                            status="detected",
                            metadata=deepcopy(target.metadata or {}),
                        )
                        mission_state.memory.add_target(discovered)
                        detected_targets.append(discovered)
                        known_target_ids.add(discovered.target_id)
                        events.append(
                            self._event(
                                timestamp,
                                updated_agent.uav_id,
                                "target_detected",
                                f"{updated_agent.uav_id} detected {discovered.target_type}.",
                                target_id=discovered.target_id,
                                severity="info",
                                metadata={
                                    "target_type": discovered.target_type,
                                    "position": discovered.position.to_dict(),
                                    "confidence": discovered.confidence,
                                },
                            )
                        )

            updated_agents.append(updated_agent)

        for event in events:
            mission_state.memory.add_event(event)
        mission_state.agents = updated_agents
        return SwarmEnvironmentTick(
            agents=updated_agents,
            events=events,
            detected_targets=detected_targets,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "base_position": self.base_position.to_dict(),
            "communication_center": self.communication_center.to_dict(),
            "communication_range": self.communication_range,
            "battery_drain_per_step": self.battery_drain_per_step,
            "low_battery_threshold": self.low_battery_threshold,
            "degraded_communication_threshold": self.degraded_communication_threshold,
            "discovery_range": self.discovery_range,
            "obstacles": [position.to_dict() for position in self.obstacles or []],
            "no_fly_zones": [position.to_dict() for position in self.no_fly_zones or []],
            "targets": [target.to_dict() for target in self.targets or []],
        }

    def _event(
        self,
        timestamp: str,
        uav_id: str,
        event_type: str,
        message: str,
        *,
        target_id: str | None = None,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> SwarmEvent:
        suffix = target_id or "environment"
        return SwarmEvent(
            event_id=f"{timestamp}:{uav_id}:{event_type}:{suffix}",
            event_type=event_type,
            message=message,
            timestamp=timestamp,
            uav_id=uav_id,
            target_id=target_id,
            severity=severity,
            metadata=metadata or {},
        )


def _position_key(position: GridPosition) -> tuple[int, int]:
    return (position.x, position.y)


def _step_delta(current: int, destination: int) -> int:
    if current < destination:
        return 1
    if current > destination:
        return -1
    return 0
