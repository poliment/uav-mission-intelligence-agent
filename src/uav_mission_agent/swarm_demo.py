from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .llm_provider import LLMProvider
from .swarm_coordinator import RoleAssignment, SwarmCoordinator, SwarmMissionPlan
from .swarm_dialogue import SwarmDialogueEngine, SwarmDialogueResult
from .swarm_environment import SwarmGridEnvironment
from .swarm_models import (
    GridPosition,
    SwarmEvent,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)


DEFAULT_SWARM_DEMO_MISSION = (
    "Use 4 UAVs to search mountain area A, prioritize a suspected thermal target, "
    "maintain one communication relay, and return low-battery aircraft to base."
)
DEMO_EVENT_ORDER: tuple[str, str, str] = (
    "target_detected",
    "battery_warning",
    "communication_degraded",
)
DEMO_PLAN_TIMESTAMP = "2026-07-10T10:00:00Z"


@dataclass
class SwarmDemoSession:
    mission_text: str
    environment: SwarmGridEnvironment
    mission_state: SwarmMissionState
    coordinator: SwarmCoordinator
    dialogue_engine: SwarmDialogueEngine
    initial_plan: SwarmMissionPlan
    current_assignments: dict[str, RoleAssignment]
    event_results: list[SwarmDialogueResult] = field(default_factory=list)
    _event_index: int = 0

    @property
    def next_event_type(self) -> str | None:
        if self._event_index >= len(DEMO_EVENT_ORDER):
            return None
        return DEMO_EVENT_ORDER[self._event_index]

    def process_next_event(self) -> SwarmDialogueResult:
        event_type = self.next_event_type
        if event_type is None:
            raise RuntimeError("all demo events have already been processed")

        event = _build_demo_event(event_type)
        working_state = deepcopy(self.mission_state)
        if event_type == "communication_degraded":
            affected = _find_agent(working_state, "UAV-1")
            affected.position = GridPosition(18, 18)
            affected.communication_quality = 0.2

        result = self.dialogue_engine.coordinate_event(event, working_state)
        self.mission_state = working_state
        for assignment in result.coordination_result.role_assignments:
            self.current_assignments[assignment.uav_id] = assignment
        self.event_results.append(result)
        self._event_index += 1
        return result

    def run_remaining_events(self) -> list[SwarmDialogueResult]:
        results: list[SwarmDialogueResult] = []
        while self.next_event_type is not None:
            results.append(self.process_next_event())
        return results

    def to_dict(self) -> dict[str, Any]:
        event_results = [result.to_dict() for result in self.event_results]
        timeline = [
            message.to_dict()
            for result in self.event_results
            for message in result.messages
        ]
        return {
            "mission_id": self.mission_state.mission_id,
            "mission_text": self.mission_text,
            "event_order": list(DEMO_EVENT_ORDER),
            "processed_event_count": len(self.event_results),
            "next_event_type": self.next_event_type,
            "environment": self.environment.to_dict(),
            "initial_plan": self.initial_plan.to_dict(),
            "event_results": event_results,
            "timeline": timeline,
            "coordinator_summaries": [
                result.coordinator_summary for result in self.event_results
            ],
            "replanning_memory": [
                event.to_dict()
                for event in self.mission_state.memory.events_by_type("replanning")
            ],
            "message_memory": [
                event.to_dict()
                for event in self.mission_state.memory.events_by_type("agent_message")
            ],
            "current_assignments": {
                uav_id: assignment.to_dict()
                for uav_id, assignment in self.current_assignments.items()
            },
            "swarm_state": self.mission_state.to_dict(),
        }


def create_swarm_demo_session(
    mission_text: str = DEFAULT_SWARM_DEMO_MISSION,
    llm_provider: LLMProvider | None = None,
) -> SwarmDemoSession:
    cleaned_mission = mission_text.strip()
    if not cleaned_mission:
        raise ValueError("mission_text must not be blank")

    environment = _build_environment()
    mission_state = _build_mission_state()
    coordinator = SwarmCoordinator(environment, llm_provider=llm_provider)
    initial_plan = coordinator.plan_mission(
        cleaned_mission,
        mission_state,
        timestamp=DEMO_PLAN_TIMESTAMP,
    )
    assignments = {
        assignment.uav_id: assignment
        for assignment in initial_plan.role_assignments
    }
    return SwarmDemoSession(
        mission_text=cleaned_mission,
        environment=environment,
        mission_state=mission_state,
        coordinator=coordinator,
        dialogue_engine=SwarmDialogueEngine(coordinator),
        initial_plan=initial_plan,
        current_assignments=assignments,
    )


def build_swarm_plan_demo_payload() -> dict[str, Any]:
    session = create_swarm_demo_session()
    payload = _common_demo_payload(session)
    payload["initial_plan"] = session.initial_plan.to_dict()
    return payload


def build_swarm_events_demo_payload() -> dict[str, Any]:
    session = create_swarm_demo_session()
    session.run_remaining_events()
    payload = _common_demo_payload(session)
    payload["event_responses"] = [
        result.coordination_result.to_dict()
        for result in session.event_results
    ]
    payload["replanning_memory"] = [
        event.to_dict()
        for event in session.mission_state.memory.events_by_type("replanning")
    ]
    return payload


def build_swarm_dialogue_demo_payload() -> dict[str, Any]:
    session = create_swarm_demo_session()
    session.run_remaining_events()
    payload = _common_demo_payload(session)
    payload["event_results"] = [result.to_dict() for result in session.event_results]
    payload["timeline"] = [
        message.to_dict()
        for result in session.event_results
        for message in result.messages
    ]
    payload["coordinator_summaries"] = [
        result.coordinator_summary for result in session.event_results
    ]
    payload["message_memory"] = [
        {
            **event.to_dict(),
            "source_message_id": event.metadata.get("message_id"),
        }
        for event in session.mission_state.memory.events_by_type("agent_message")
    ]
    return payload


def _common_demo_payload(session: SwarmDemoSession) -> dict[str, Any]:
    return {
        "status": "ok",
        "demo": "swarm",
        "mission_id": session.mission_state.mission_id,
        "mission_text": session.mission_text,
        "swarm_state": session.mission_state.to_dict(),
    }


def _build_environment() -> SwarmGridEnvironment:
    return SwarmGridEnvironment(
        width=20,
        height=20,
        base_position=GridPosition(0, 0),
        communication_center=GridPosition(0, 0),
        communication_range=24.0,
        obstacles=[GridPosition(6, 5), GridPosition(6, 6)],
        no_fly_zones=[GridPosition(8, 8)],
        battery_drain_per_step=1.0,
        low_battery_threshold=25.0,
    )


def _build_mission_state() -> SwarmMissionState:
    return SwarmMissionState(
        mission_id="demo-swarm-mountain-a",
        agents=[
            UAVAgentState("UAV-1", "unassigned", GridPosition(0, 0), 92.0),
            UAVAgentState("UAV-2", "unassigned", GridPosition(1, 0), 88.0),
            UAVAgentState("UAV-3", "unassigned", GridPosition(0, 1), 84.0),
            UAVAgentState("UAV-4", "unassigned", GridPosition(1, 1), 76.0),
        ],
        memory=SwarmMemory(),
        base_position=GridPosition(0, 0),
        grid_size={"width": 20, "height": 20},
    )


def _build_demo_event(event_type: str) -> SwarmEvent:
    if event_type == "target_detected":
        return SwarmEvent(
            event_id="demo-event-target-detected",
            event_type=event_type,
            message="UAV-1 detected a suspected thermal source.",
            timestamp="2026-07-10T10:05:00Z",
            uav_id="UAV-1",
            target_id="target-thermal-1",
            area_id="mountain-area-a-east",
            metadata={
                "target_type": "thermal_source",
                "position": {"x": 12, "y": 8},
                "confidence": 0.91,
            },
        )
    if event_type == "battery_warning":
        return SwarmEvent(
            event_id="demo-event-battery-warning",
            event_type=event_type,
            message="UAV-2 battery dropped below the reserve threshold.",
            timestamp="2026-07-10T10:08:00Z",
            uav_id="UAV-2",
            severity="warning",
            metadata={"battery_level": 20.0},
        )
    if event_type == "communication_degraded":
        return SwarmEvent(
            event_id="demo-event-communication-degraded",
            event_type=event_type,
            message="UAV-1 communication quality dropped below threshold.",
            timestamp="2026-07-10T10:10:00Z",
            uav_id="UAV-1",
            severity="warning",
            metadata={"communication_quality": 0.2},
        )
    raise ValueError(f"unsupported demo event type: {event_type}")


def _find_agent(mission_state: SwarmMissionState, uav_id: str) -> UAVAgentState:
    for agent in mission_state.agents:
        if agent.uav_id == uav_id:
            return agent
    raise ValueError(f"unknown UAV: {uav_id}")
