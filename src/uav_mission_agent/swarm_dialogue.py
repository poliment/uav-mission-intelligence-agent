from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .swarm_coordinator import SwarmCoordinator, SwarmReplanResult
from .swarm_models import SwarmEvent, SwarmMissionState


@dataclass
class SwarmAgentMessage:
    message_id: str
    timestamp: str
    sender_id: str
    recipient_ids: list[str]
    message_type: str
    content: str
    trigger_event_id: str
    related_uav_id: str | None = None
    target_id: str | None = None
    memory_event_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.recipient_ids = list(self.recipient_ids)
        self.metadata = deepcopy(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender_id": self.sender_id,
            "recipient_ids": list(self.recipient_ids),
            "message_type": self.message_type,
            "content": self.content,
            "trigger_event_id": self.trigger_event_id,
            "related_uav_id": self.related_uav_id,
            "target_id": self.target_id,
            "memory_event_id": self.memory_event_id,
            "metadata": deepcopy(self.metadata),
        }


@dataclass
class SwarmDialogueResult:
    mission_id: str
    trigger_event: SwarmEvent
    messages: list[SwarmAgentMessage]
    coordinator_summary: str
    coordination_result: SwarmReplanResult
    memory_updates: list[SwarmEvent]
    swarm_state: SwarmMissionState

    def to_dict(self) -> dict[str, Any]:
        coordination_data = self.coordination_result.to_dict()
        return {
            "result_type": "swarm_dialogue",
            "mission_id": self.mission_id,
            "trigger_event": self.trigger_event.to_dict(),
            "messages": [message.to_dict() for message in self.messages],
            "coordinator_summary": self.coordinator_summary,
            "coordination_result": coordination_data,
            "assignment_changes": deepcopy(coordination_data["assignment_changes"]),
            "algorithm_checks": deepcopy(coordination_data["algorithm_checks"]),
            "memory_updates": [event.to_dict() for event in self.memory_updates],
            "swarm_state": self.swarm_state.to_dict(),
        }


class SwarmDialogueEngine:
    coordinator_id = "SWARM-COORDINATOR"

    def __init__(self, coordinator: SwarmCoordinator) -> None:
        self.coordinator = coordinator

    def coordinate_event(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> SwarmDialogueResult:
        supported_event_types = {
            "target_detected",
            "battery_warning",
            "communication_degraded",
        }
        if event.event_type not in supported_event_types:
            raise ValueError(f"unsupported dialogue event type: {event.event_type}")
        if not event.uav_id:
            raise ValueError(f"{event.event_type} dialogue event requires uav_id")

        coordination_result = self.coordinator.replan_for_event(event, mission_state)
        if not coordination_result.assignment_changes:
            return self._empty_result(event, mission_state, coordination_result)

        if event.event_type == "target_detected":
            specs = self._target_message_specs(
                event,
                mission_state,
                coordination_result,
            )
        elif event.event_type == "battery_warning":
            specs = self._battery_message_specs(
                event,
                mission_state,
                coordination_result,
            )
        else:
            specs = self._communication_message_specs(
                event,
                mission_state,
                coordination_result,
            )
        messages, memory_updates = self._record_message_specs(
            specs,
            event,
            mission_state,
        )
        summary = messages[-1].content
        return SwarmDialogueResult(
            mission_id=mission_state.mission_id,
            trigger_event=deepcopy(event),
            messages=messages,
            coordinator_summary=summary,
            coordination_result=coordination_result,
            memory_updates=memory_updates,
            swarm_state=deepcopy(mission_state),
        )

    def _target_message_specs(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
        coordination_result: SwarmReplanResult,
    ) -> list[dict[str, Any]]:
        change = coordination_result.assignment_changes[0]
        selected_uav = change.uav_id
        position = event.metadata.get("position", {})
        confidence = event.metadata.get("confidence")
        target_label = event.target_id or "unknown-target"
        report_content = (
            f"{event.uav_id} reports {target_label} at "
            f"({position.get('x')}, {position.get('y')}) with confidence {confidence}."
        )
        acknowledgement_recipients = self._recipient_ids(
            selected_uav,
            [self.coordinator_id, event.uav_id],
        )
        all_uavs = sorted(agent.uav_id for agent in mission_state.agents)
        algorithm_checks = [
            assignment.algorithm_checks_to_dict()
            for assignment in coordination_result.role_assignments
        ]
        return [
            {
                "sender_id": event.uav_id,
                "recipient_ids": [self.coordinator_id],
                "message_type": "target_report",
                "content": report_content,
                "related_uav_id": selected_uav,
                "target_id": event.target_id,
                "metadata": {
                    "target_type": event.metadata.get("target_type"),
                    "position": deepcopy(position),
                    "confidence": confidence,
                },
            },
            {
                "sender_id": selected_uav,
                "recipient_ids": acknowledgement_recipients,
                "message_type": "task_acknowledgement",
                "content": (
                    f"{selected_uav} accepts tracker assignment for {target_label}."
                ),
                "related_uav_id": event.uav_id,
                "target_id": event.target_id,
                "metadata": {
                    "assignment_change": change.to_dict(),
                    "algorithm_checks": deepcopy(algorithm_checks),
                },
            },
            {
                "sender_id": self.coordinator_id,
                "recipient_ids": all_uavs,
                "message_type": "coordination_summary",
                "content": coordination_result.decision_rationale,
                "related_uav_id": selected_uav,
                "target_id": event.target_id,
                "metadata": {
                    "decision_source": coordination_result.decision_source,
                    "assignment_change_uav_ids": [selected_uav],
                    "algorithm_checks": deepcopy(algorithm_checks),
                },
            },
        ]

    def _battery_message_specs(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
        coordination_result: SwarmReplanResult,
    ) -> list[dict[str, Any]]:
        changes = coordination_result.assignment_changes
        replacement_changes = [
            change for change in changes if change.uav_id != event.uav_id
        ]
        algorithm_checks = [
            assignment.algorithm_checks_to_dict()
            for assignment in coordination_result.role_assignments
        ]
        specs: list[dict[str, Any]] = [
            {
                "sender_id": event.uav_id,
                "recipient_ids": [self.coordinator_id],
                "message_type": "battery_status",
                "content": (
                    f"{event.uav_id} reports battery level "
                    f"{event.metadata.get('battery_level')} and requests return to base."
                ),
                "related_uav_id": event.uav_id,
                "target_id": event.target_id,
                "metadata": {
                    "battery_level": event.metadata.get("battery_level"),
                    "low_battery_threshold": (
                        self.coordinator.environment.low_battery_threshold
                    ),
                },
            }
        ]
        if replacement_changes:
            replacement = replacement_changes[0]
            specs.append(
                {
                    "sender_id": replacement.uav_id,
                    "recipient_ids": self._dedupe_ids(
                        [self.coordinator_id, event.uav_id]
                    ),
                    "message_type": "task_handoff",
                    "content": (
                        f"{replacement.uav_id} accepts the "
                        f"{replacement.after.get('role')} assignment from {event.uav_id}."
                    ),
                    "related_uav_id": event.uav_id,
                    "target_id": event.target_id,
                    "metadata": {
                        "assignment_change": replacement.to_dict(),
                        "algorithm_checks": deepcopy(algorithm_checks),
                    },
                }
            )
        specs.append(
            {
                "sender_id": self.coordinator_id,
                "recipient_ids": sorted(
                    agent.uav_id for agent in mission_state.agents
                ),
                "message_type": "coordination_summary",
                "content": coordination_result.decision_rationale,
                "related_uav_id": event.uav_id,
                "target_id": event.target_id,
                "metadata": {
                    "decision_source": coordination_result.decision_source,
                    "assignment_change_uav_ids": [
                        change.uav_id for change in changes
                    ],
                    "algorithm_checks": deepcopy(algorithm_checks),
                },
            }
        )
        return specs

    def _communication_message_specs(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
        coordination_result: SwarmReplanResult,
    ) -> list[dict[str, Any]]:
        changes = coordination_result.assignment_changes
        algorithm_checks = [
            assignment.algorithm_checks_to_dict()
            for assignment in coordination_result.role_assignments
        ]
        specs: list[dict[str, Any]] = [
            {
                "sender_id": event.uav_id,
                "recipient_ids": [self.coordinator_id],
                "message_type": "communication_status",
                "content": (
                    f"{event.uav_id} reports communication quality "
                    f"{event.metadata.get('communication_quality')}."
                ),
                "related_uav_id": event.uav_id,
                "target_id": event.target_id,
                "metadata": {
                    "communication_quality": event.metadata.get(
                        "communication_quality"
                    ),
                    "required_quality": (
                        self.coordinator.environment.degraded_communication_threshold
                    ),
                },
            }
        ]
        if changes:
            relay_change = changes[0]
            specs.append(
                {
                    "sender_id": relay_change.uav_id,
                    "recipient_ids": self._dedupe_ids(
                        [self.coordinator_id, event.uav_id]
                    ),
                    "message_type": "relay_acknowledgement",
                    "content": (
                        f"{relay_change.uav_id} accepts relay support for "
                        f"{event.uav_id} at "
                        f"{relay_change.after.get('waypoint')}."
                    ),
                    "related_uav_id": event.uav_id,
                    "target_id": event.target_id,
                    "metadata": {
                        "assignment_change": relay_change.to_dict(),
                        "algorithm_checks": deepcopy(algorithm_checks),
                    },
                }
            )
        specs.append(
            {
                "sender_id": self.coordinator_id,
                "recipient_ids": sorted(
                    agent.uav_id for agent in mission_state.agents
                ),
                "message_type": "coordination_summary",
                "content": coordination_result.decision_rationale,
                "related_uav_id": event.uav_id,
                "target_id": event.target_id,
                "metadata": {
                    "decision_source": coordination_result.decision_source,
                    "assignment_change_uav_ids": [
                        change.uav_id for change in changes
                    ],
                    "algorithm_checks": deepcopy(algorithm_checks),
                },
            }
        )
        return specs

    def _record_message_specs(
        self,
        specs: list[dict[str, Any]],
        trigger_event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> tuple[list[SwarmAgentMessage], list[SwarmEvent]]:
        messages: list[SwarmAgentMessage] = []
        memory_updates: list[SwarmEvent] = []
        for spec in specs:
            message = SwarmAgentMessage(
                message_id=self._next_message_id(mission_state),
                timestamp=trigger_event.timestamp,
                sender_id=spec["sender_id"],
                recipient_ids=spec["recipient_ids"],
                message_type=spec["message_type"],
                content=spec["content"],
                trigger_event_id=trigger_event.event_id,
                related_uav_id=spec.get("related_uav_id"),
                target_id=spec.get("target_id"),
                metadata=spec.get("metadata", {}),
            )
            memory_event = self._store_message(message, trigger_event, mission_state)
            messages.append(message)
            memory_updates.append(memory_event)
        return messages, memory_updates

    def _store_message(
        self,
        message: SwarmAgentMessage,
        trigger_event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> SwarmEvent:
        event_id = self._unique_event_id(
            f"{message.message_id}-memory",
            mission_state,
        )
        memory_event = SwarmEvent(
            event_id=event_id,
            event_type="agent_message",
            message=message.content,
            timestamp=message.timestamp,
            uav_id=(
                message.sender_id
                if self._has_agent(mission_state, message.sender_id)
                else None
            ),
            target_id=message.target_id,
            area_id=trigger_event.area_id,
            metadata={
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "recipient_ids": list(message.recipient_ids),
                "message_type": message.message_type,
                "trigger_event_id": message.trigger_event_id,
                "related_uav_id": message.related_uav_id,
                "message_metadata": deepcopy(message.metadata),
            },
        )
        mission_state.memory.add_event(memory_event)
        message.memory_event_id = memory_event.event_id
        linked_uav_ids = self._dedupe_ids(
            [message.sender_id, *message.recipient_ids]
        )
        for uav_id in linked_uav_ids:
            agent = self._find_agent(mission_state, uav_id)
            if agent is not None and memory_event.event_id not in agent.memory_refs:
                agent.memory_refs.append(memory_event.event_id)
        return memory_event

    @staticmethod
    def _next_message_id(mission_state: SwarmMissionState) -> str:
        existing = {
            event.metadata.get("message_id")
            for event in mission_state.memory.events
            if event.event_type == "agent_message"
        }
        sequence = len(existing) + 1
        while True:
            candidate = f"{mission_state.mission_id}-msg-{sequence:03d}"
            if candidate not in existing:
                return candidate
            sequence += 1

    @staticmethod
    def _unique_event_id(
        preferred: str,
        mission_state: SwarmMissionState,
    ) -> str:
        existing = {event.event_id for event in mission_state.memory.events}
        if preferred not in existing:
            return preferred
        sequence = 2
        while f"{preferred}-{sequence}" in existing:
            sequence += 1
        return f"{preferred}-{sequence}"

    @staticmethod
    def _find_agent(mission_state: SwarmMissionState, uav_id: str):
        for agent in mission_state.agents:
            if agent.uav_id == uav_id:
                return agent
        return None

    @classmethod
    def _has_agent(cls, mission_state: SwarmMissionState, uav_id: str) -> bool:
        return cls._find_agent(mission_state, uav_id) is not None

    @staticmethod
    def _dedupe_ids(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @classmethod
    def _recipient_ids(cls, sender_id: str, values: list[str]) -> list[str]:
        return [value for value in cls._dedupe_ids(values) if value != sender_id]

    @staticmethod
    def _empty_result(
        event: SwarmEvent,
        mission_state: SwarmMissionState,
        coordination_result: SwarmReplanResult,
    ) -> SwarmDialogueResult:
        return SwarmDialogueResult(
            mission_id=mission_state.mission_id,
            trigger_event=deepcopy(event),
            messages=[],
            coordinator_summary=coordination_result.decision_rationale,
            coordination_result=coordination_result,
            memory_updates=[],
            swarm_state=deepcopy(mission_state),
        )
