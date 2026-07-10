from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .llm_provider import LLMProvider
from .models import TaskSpec
from .swarm_algorithms import (
    AStarPathResult,
    ConstraintCheck,
    astar_path,
    check_battery_feasibility,
    check_communication_coverage,
    score_candidate_for_target,
)
from .swarm_environment import SwarmGridEnvironment
from .swarm_models import (
    DetectedTarget,
    GridPosition,
    SwarmEvent,
    SwarmMissionState,
    UAVAgentState,
)
from .task_parser import parse_task


@dataclass
class RoleAssignment:
    uav_id: str
    role: str
    assigned_area: str | None
    objective: str
    waypoint: GridPosition
    path: AStarPathResult
    battery_check: ConstraintCheck
    communication_check: ConstraintCheck
    reason: str

    @property
    def feasible(self) -> bool:
        return (
            self.path.reachable
            and self.battery_check.passed
            and self.communication_check.passed
        )

    def algorithm_checks_to_dict(self) -> dict[str, Any]:
        return {
            "uav_id": self.uav_id,
            "role": self.role,
            "feasible": self.feasible,
            "path": self.path.to_dict(),
            "battery": self.battery_check.to_dict(),
            "communication": self.communication_check.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "uav_id": self.uav_id,
            "role": self.role,
            "assigned_area": self.assigned_area,
            "objective": self.objective,
            "waypoint": self.waypoint.to_dict(),
            "feasible": self.feasible,
            "reason": self.reason,
            "algorithm_checks": self.algorithm_checks_to_dict(),
        }


@dataclass
class SwarmMissionPlan:
    mission_id: str
    mission_text: str
    task: TaskSpec
    decision_source: str
    decision_rationale: str
    role_assignments: list[RoleAssignment]
    memory_updates: list[SwarmEvent]
    swarm_state: SwarmMissionState
    provider_advisory: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": "swarm_mission_plan",
            "mission_id": self.mission_id,
            "mission_text": self.mission_text,
            "task": self.task.to_dict(),
            "decision_source": self.decision_source,
            "decision_rationale": self.decision_rationale,
            "role_assignments": [assignment.to_dict() for assignment in self.role_assignments],
            "algorithm_checks": [
                assignment.algorithm_checks_to_dict()
                for assignment in self.role_assignments
            ],
            "memory_updates": [event.to_dict() for event in self.memory_updates],
            "provider_advisory": deepcopy(self.provider_advisory),
            "swarm_state": self.swarm_state.to_dict(),
        }


@dataclass
class AssignmentChange:
    uav_id: str
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "uav_id": self.uav_id,
            "before": deepcopy(self.before),
            "after": deepcopy(self.after),
            "reason": self.reason,
        }


@dataclass
class SwarmReplanResult:
    mission_id: str
    trigger_event: SwarmEvent
    decision_source: str
    decision_rationale: str
    assignment_changes: list[AssignmentChange]
    role_assignments: list[RoleAssignment]
    memory_updates: list[SwarmEvent]
    swarm_state: SwarmMissionState
    provider_advisory: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": "swarm_replan",
            "mission_id": self.mission_id,
            "trigger_event": self.trigger_event.to_dict(),
            "decision_source": self.decision_source,
            "decision_rationale": self.decision_rationale,
            "assignment_changes": [change.to_dict() for change in self.assignment_changes],
            "role_assignments": [assignment.to_dict() for assignment in self.role_assignments],
            "algorithm_checks": [
                assignment.algorithm_checks_to_dict()
                for assignment in self.role_assignments
            ],
            "memory_updates": [event.to_dict() for event in self.memory_updates],
            "provider_advisory": deepcopy(self.provider_advisory),
            "swarm_state": self.swarm_state.to_dict(),
        }


class SwarmCoordinator:
    def __init__(
        self,
        environment: SwarmGridEnvironment,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.environment = environment
        self.llm_provider = llm_provider

    def plan_mission(
        self,
        mission_text: str,
        mission_state: SwarmMissionState,
        *,
        timestamp: str,
    ) -> SwarmMissionPlan:
        if not mission_text.strip():
            raise ValueError("mission_text must not be blank")
        if not mission_state.agents:
            raise ValueError("mission state must contain at least one agent")
        self._validate_grid_size(mission_state)

        task = parse_task(mission_text)
        roles = self._select_roles(task, mission_text, mission_state.agents)
        assignments = self._build_mission_assignments(
            task,
            mission_text,
            mission_state,
            roles,
        )
        memory_updates = self._record_initial_plan(
            mission_text,
            mission_state,
            assignments,
            timestamp,
        )
        mission_state.phase = "planned"

        rationale = self._offline_plan_rationale(assignments)
        plan = SwarmMissionPlan(
            mission_id=mission_state.mission_id,
            mission_text=mission_text.strip(),
            task=task,
            decision_source="offline_rules",
            decision_rationale=rationale,
            role_assignments=assignments,
            memory_updates=memory_updates,
            swarm_state=deepcopy(mission_state),
        )
        return self._enhance_plan_with_provider(plan)

    def _enhance_plan_with_provider(
        self,
        plan: SwarmMissionPlan,
    ) -> SwarmMissionPlan:
        if self.llm_provider is None:
            return plan

        baseline_plan = plan.to_dict()
        provider_name = getattr(self.llm_provider, "provider_name", "unknown")
        provider_model = getattr(self.llm_provider, "model", None)
        try:
            response = self.llm_provider.generate_plan(
                task=plan.task.to_dict(),
                retrieved_knowledge=[
                    {
                        "topic": "swarm_memory_event",
                        "content": event.message,
                        "tags": [event.event_type, event.severity],
                    }
                    for event in plan.memory_updates
                ],
                baseline_plan=deepcopy(baseline_plan),
                output_schema={
                    "type": "object",
                    "required": ["recommendations", "risks", "mission_config"],
                    "properties": {
                        "recommendations": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "risks": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "mission_config": {"type": "object"},
                    },
                },
            )
            if not isinstance(response, dict):
                raise ValueError("provider response must be an object")
            recommendations = self._string_list(response.get("recommendations"))
            risks = self._string_list(response.get("risks"))
            plan.provider_advisory = {
                "provider": provider_name,
                "model": provider_model,
                "status": "applied",
                "recommendations": recommendations,
                "risks": risks,
            }
            if recommendations or risks:
                plan.decision_source = "provider_enhanced"
                advisory_text = " ".join(recommendations + risks)
                plan.decision_rationale = (
                    f"{plan.decision_rationale} Provider advisory: {advisory_text}"
                )
        except Exception as exc:
            plan.provider_advisory = {
                "provider": provider_name,
                "model": provider_model,
                "status": "offline_fallback",
                "error_type": type(exc).__name__,
            }
            plan.decision_rationale = (
                f"{plan.decision_rationale} Provider enhancement was unavailable; "
                "the offline decision was retained."
            )
        return plan

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    def replan_for_event(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> SwarmReplanResult:
        self._validate_grid_size(mission_state)
        if self._event_was_replanned(event, mission_state):
            return SwarmReplanResult(
                mission_id=mission_state.mission_id,
                trigger_event=deepcopy(event),
                decision_source="offline_rules",
                decision_rationale=(
                    f"Event {event.event_id} was already processed; the existing "
                    "swarm assignment was retained."
                ),
                assignment_changes=[],
                role_assignments=[],
                memory_updates=[],
                swarm_state=deepcopy(mission_state),
            )
        if event.event_type == "battery_warning":
            return self._replan_low_battery(event, mission_state)
        if event.event_type == "target_detected":
            return self._replan_target_detected(event, mission_state)
        if event.event_type == "communication_degraded":
            return self._replan_communication_degraded(event, mission_state)
        raise ValueError(f"unsupported swarm event type: {event.event_type}")

    def _replan_low_battery(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> SwarmReplanResult:
        affected = self._require_event_agent(event, mission_state)
        battery_level = event.metadata.get("battery_level")
        if battery_level is not None:
            if not isinstance(battery_level, (int, float)) or not 0 <= battery_level <= 100:
                raise ValueError("battery_warning metadata battery_level must be within 0..100")
            affected.battery_level = float(battery_level)

        prior_waypoint = self._latest_assignment_waypoint(
            mission_state,
            affected.uav_id,
            affected.position,
        )
        prior_role = affected.role
        prior_area = affected.assigned_area
        prior_objective = affected.current_objective or "Continue assigned mission"
        changes: list[AssignmentChange] = []
        checked_assignments: list[RoleAssignment] = []

        affected_before = self._assignment_snapshot(affected, prior_waypoint)
        return_assignment = self._checked_assignment(
            affected,
            role="returning",
            assigned_area="base",
            objective="Return to base due to battery warning",
            waypoint=mission_state.base_position,
        )
        self._apply_assignment(affected, return_assignment)
        changes.append(
            AssignmentChange(
                uav_id=affected.uav_id,
                before=affected_before,
                after=self._assignment_snapshot(affected, return_assignment.waypoint),
                reason="Battery warning requires immediate return to base.",
            )
        )
        checked_assignments.append(return_assignment)

        replacement_assignment = self._find_replacement_assignment(
            mission_state,
            excluded_uav_id=affected.uav_id,
            role=prior_role,
            assigned_area=prior_area,
            objective=prior_objective,
            waypoint=prior_waypoint,
        )
        if replacement_assignment is not None:
            replacement = self._agent_by_id(
                mission_state,
                replacement_assignment.uav_id,
            )
            replacement_before = self._assignment_snapshot(
                replacement,
                replacement.position,
            )
            self._apply_assignment(replacement, replacement_assignment)
            changes.append(
                AssignmentChange(
                    uav_id=replacement.uav_id,
                    before=replacement_before,
                    after=self._assignment_snapshot(
                        replacement,
                        replacement_assignment.waypoint,
                    ),
                    reason=(
                        f"Took over {affected.uav_id}'s {prior_role} assignment "
                        "after feasibility checks passed."
                    ),
                )
            )
            checked_assignments.append(replacement_assignment)

        memory_updates = self._store_trigger_event(event, mission_state)
        replanning_event = self._append_event(
            mission_state,
            event_type="replanning",
            message="Swarm coordinator replanned after a battery warning.",
            timestamp=event.timestamp,
            uav_id=affected.uav_id,
            area_id=prior_area,
            severity="warning",
            metadata={
                "trigger_event_id": event.event_id,
                "assignment_changes": [change.to_dict() for change in changes],
                "algorithm_checks": [
                    assignment.algorithm_checks_to_dict()
                    for assignment in checked_assignments
                ],
            },
        )
        memory_updates.append(replanning_event)
        for change in changes:
            agent = self._agent_by_id(mission_state, change.uav_id)
            if event.event_id not in agent.memory_refs and change.uav_id == affected.uav_id:
                agent.memory_refs.append(event.event_id)
            agent.memory_refs.append(replanning_event.event_id)
        mission_state.phase = "replanned"

        replacement_text = (
            f" {replacement_assignment.uav_id} took over the {prior_role} assignment."
            if replacement_assignment is not None
            else " No feasible replacement was available."
        )
        rationale = (
            f"Offline rules returned {affected.uav_id} to base after the battery warning."
            f"{replacement_text} A*, battery, and communication checks remain authoritative."
        )
        return SwarmReplanResult(
            mission_id=mission_state.mission_id,
            trigger_event=deepcopy(event),
            decision_source="offline_rules",
            decision_rationale=rationale,
            assignment_changes=changes,
            role_assignments=checked_assignments,
            memory_updates=memory_updates,
            swarm_state=deepcopy(mission_state),
        )

    def _replan_target_detected(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> SwarmReplanResult:
        target, is_new_target = self._target_from_event(event, mission_state)
        candidates = []
        for agent in mission_state.agents:
            if (
                agent.role == "returning"
                or agent.battery_level <= self.environment.low_battery_threshold
            ):
                continue
            score = score_candidate_for_target(agent, target, self.environment)
            if (
                score.path.reachable
                and score.battery_check.passed
                and score.communication_check.passed
            ):
                candidates.append(score)
        candidates.sort(key=lambda score: (-score.score, score.uav_id))
        if not candidates:
            raise ValueError(f"no feasible UAV candidate for target {target.target_id}")

        best = candidates[0]
        tracker = self._agent_by_id(mission_state, best.uav_id)
        prior_waypoint = self._latest_assignment_waypoint(
            mission_state,
            tracker.uav_id,
            tracker.position,
        )
        before = self._assignment_snapshot(tracker, prior_waypoint)
        assignment = RoleAssignment(
            uav_id=tracker.uav_id,
            role="tracker",
            assigned_area=target.target_id,
            objective=f"Track detected target {target.target_id}",
            waypoint=GridPosition(target.position.x, target.position.y),
            path=best.path,
            battery_check=best.battery_check,
            communication_check=best.communication_check,
            reason=(
                f"Offline target candidate score {best.score}: {best.explanation}."
            ),
        )
        self._apply_assignment(tracker, assignment)
        change = AssignmentChange(
            uav_id=tracker.uav_id,
            before=before,
            after=self._assignment_snapshot(tracker, assignment.waypoint),
            reason=(
                f"Selected the highest-scoring feasible UAV for {target.target_id}."
            ),
        )

        memory_updates = self._store_trigger_event(event, mission_state)
        if is_new_target:
            mission_state.memory.add_target(target)
        replanning_event = self._append_event(
            mission_state,
            event_type="replanning",
            message="Swarm coordinator assigned a tracker after target detection.",
            timestamp=event.timestamp,
            uav_id=tracker.uav_id,
            target_id=target.target_id,
            area_id=event.area_id,
            metadata={
                "trigger_event_id": event.event_id,
                "assignment_changes": [change.to_dict()],
                "algorithm_checks": [assignment.algorithm_checks_to_dict()],
                "candidate_score": best.score,
            },
        )
        memory_updates.append(replanning_event)
        if event.event_id not in tracker.memory_refs:
            tracker.memory_refs.append(event.event_id)
        tracker.memory_refs.append(replanning_event.event_id)
        mission_state.phase = "replanned"

        rationale = (
            f"Offline rules assigned {tracker.uav_id} to track {target.target_id} "
            f"with candidate score {best.score}. A*, battery, and communication "
            "checks all passed before the state changed."
        )
        return SwarmReplanResult(
            mission_id=mission_state.mission_id,
            trigger_event=deepcopy(event),
            decision_source="offline_rules",
            decision_rationale=rationale,
            assignment_changes=[change],
            role_assignments=[assignment],
            memory_updates=memory_updates,
            swarm_state=deepcopy(mission_state),
        )

    def _replan_communication_degraded(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> SwarmReplanResult:
        affected = self._require_event_agent(event, mission_state)
        communication_quality = event.metadata.get("communication_quality")
        if communication_quality is not None:
            if (
                not isinstance(communication_quality, (int, float))
                or not 0 <= communication_quality <= 1
            ):
                raise ValueError(
                    "communication_degraded metadata communication_quality must be within 0..1"
                )
            affected.communication_quality = float(communication_quality)

        relay_waypoint = self._safe_relay_waypoint(affected.position)
        relay_assignment = self._find_relay_assignment(
            mission_state,
            affected_uav_id=affected.uav_id,
            waypoint=relay_waypoint,
        )
        if relay_assignment is None:
            raise ValueError(f"no feasible relay candidate for {affected.uav_id}")

        relay = self._agent_by_id(mission_state, relay_assignment.uav_id)
        prior_waypoint = self._latest_assignment_waypoint(
            mission_state,
            relay.uav_id,
            relay.position,
        )
        before = self._assignment_snapshot(relay, prior_waypoint)
        self._apply_assignment(relay, relay_assignment)
        change = AssignmentChange(
            uav_id=relay.uav_id,
            before=before,
            after=self._assignment_snapshot(relay, relay_assignment.waypoint),
            reason=(
                f"Positioned relay support at the farthest safe communication point "
                f"toward {affected.uav_id}."
            ),
        )

        memory_updates = self._store_trigger_event(event, mission_state)
        replanning_event = self._append_event(
            mission_state,
            event_type="replanning",
            message="Swarm coordinator repositioned relay support after link degradation.",
            timestamp=event.timestamp,
            uav_id=relay.uav_id,
            area_id=relay_assignment.assigned_area,
            severity="warning",
            metadata={
                "trigger_event_id": event.event_id,
                "affected_uav_id": affected.uav_id,
                "assignment_changes": [change.to_dict()],
                "algorithm_checks": [relay_assignment.algorithm_checks_to_dict()],
            },
        )
        memory_updates.append(replanning_event)
        if event.event_id not in affected.memory_refs:
            affected.memory_refs.append(event.event_id)
        affected.memory_refs.append(replanning_event.event_id)
        if relay.uav_id != affected.uav_id:
            relay.memory_refs.append(replanning_event.event_id)
        mission_state.phase = "replanned"

        rationale = (
            f"Offline rules assigned {relay.uav_id} as communication relay support for "
            f"{affected.uav_id}. The selected waypoint stays above communication quality "
            f"{self.environment.degraded_communication_threshold}, and its A*, battery, "
            "and communication checks passed."
        )
        return SwarmReplanResult(
            mission_id=mission_state.mission_id,
            trigger_event=deepcopy(event),
            decision_source="offline_rules",
            decision_rationale=rationale,
            assignment_changes=[change],
            role_assignments=[relay_assignment],
            memory_updates=memory_updates,
            swarm_state=deepcopy(mission_state),
        )

    def _validate_grid_size(self, mission_state: SwarmMissionState) -> None:
        if mission_state.grid_size is None:
            return
        expected = {
            "width": self.environment.width,
            "height": self.environment.height,
        }
        if mission_state.grid_size != expected:
            raise ValueError("mission grid_size must match coordinator environment")

    def _require_event_agent(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> UAVAgentState:
        if not event.uav_id:
            raise ValueError(f"{event.event_type} event requires uav_id")
        return self._agent_by_id(mission_state, event.uav_id)

    def _target_from_event(
        self,
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> tuple[DetectedTarget, bool]:
        if not event.target_id:
            raise ValueError("target_detected event requires target_id")
        for target in mission_state.memory.targets:
            if target.target_id == event.target_id:
                return target, False

        target_type = event.metadata.get("target_type")
        position = event.metadata.get("position")
        confidence = event.metadata.get("confidence")
        if not isinstance(target_type, str) or not target_type.strip():
            raise ValueError("target_detected event requires metadata target_type")
        if not isinstance(position, dict):
            raise ValueError("target_detected event requires metadata position")
        x = position.get("x")
        y = position.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("target_detected metadata position requires integer x and y")
        if not isinstance(confidence, (int, float)):
            raise ValueError("target_detected event requires numeric metadata confidence")
        target_position = GridPosition(x, y)
        if not self.environment.in_bounds(target_position):
            raise ValueError("target_detected position must be inside the environment")
        target = DetectedTarget(
            target_id=event.target_id,
            target_type=target_type.strip(),
            position=target_position,
            confidence=float(confidence),
            detected_by=event.uav_id or "swarm-event",
            timestamp=event.timestamp,
            status="queued_for_tracking",
            metadata={"source_event_id": event.event_id},
        )
        return target, True

    @staticmethod
    def _agent_by_id(
        mission_state: SwarmMissionState,
        uav_id: str,
    ) -> UAVAgentState:
        for agent in mission_state.agents:
            if agent.uav_id == uav_id:
                return agent
        raise ValueError(f"unknown UAV agent: {uav_id}")

    @classmethod
    def _latest_assignment_waypoint(
        cls,
        mission_state: SwarmMissionState,
        uav_id: str,
        fallback: GridPosition,
    ) -> GridPosition:
        for event in reversed(mission_state.memory.events):
            if event.event_type == "replanning":
                changes = event.metadata.get("assignment_changes")
                if isinstance(changes, list):
                    for change in reversed(changes):
                        if not isinstance(change, dict) or change.get("uav_id") != uav_id:
                            continue
                        after = change.get("after")
                        if isinstance(after, dict):
                            waypoint = cls._position_from_mapping(after.get("waypoint"))
                            if waypoint is not None:
                                return waypoint
            if event.event_type == "area_assigned" and event.uav_id == uav_id:
                waypoint = cls._position_from_mapping(event.metadata.get("waypoint"))
                if waypoint is not None:
                    return waypoint
        return GridPosition(fallback.x, fallback.y)

    @staticmethod
    def _position_from_mapping(value: Any) -> GridPosition | None:
        if not isinstance(value, dict):
            return None
        x = value.get("x")
        y = value.get("y")
        if type(x) is not int or type(y) is not int:
            return None
        return GridPosition(x, y)

    def _find_replacement_assignment(
        self,
        mission_state: SwarmMissionState,
        *,
        excluded_uav_id: str,
        role: str,
        assigned_area: str | None,
        objective: str,
        waypoint: GridPosition,
    ) -> RoleAssignment | None:
        candidates = [
            agent
            for agent in mission_state.agents
            if agent.uav_id != excluded_uav_id
            and agent.role != "returning"
            and agent.battery_level > self.environment.low_battery_threshold
        ]
        candidates.sort(
            key=lambda agent: (
                0 if agent.role == "reserve" else 1,
                -agent.battery_level,
                -agent.communication_quality,
                agent.uav_id,
            )
        )
        for candidate in candidates:
            assignment = self._checked_assignment(
                candidate,
                role=role,
                assigned_area=assigned_area,
                objective=objective,
                waypoint=waypoint,
            )
            if assignment.feasible:
                return assignment
        return None

    def _find_relay_assignment(
        self,
        mission_state: SwarmMissionState,
        *,
        affected_uav_id: str,
        waypoint: GridPosition,
    ) -> RoleAssignment | None:
        candidates = [
            agent
            for agent in mission_state.agents
            if agent.uav_id != affected_uav_id
            and agent.role != "returning"
            and agent.battery_level > self.environment.low_battery_threshold
        ]
        candidates.sort(
            key=lambda agent: (
                0 if agent.role == "relay" else 1 if agent.role == "reserve" else 2,
                -agent.battery_level,
                -agent.communication_quality,
                agent.uav_id,
            )
        )
        for candidate in candidates:
            assignment = self._checked_assignment(
                candidate,
                role="relay",
                assigned_area=f"relay-support-{affected_uav_id}",
                objective=f"Restore communication support for {affected_uav_id}",
                waypoint=waypoint,
            )
            if assignment.feasible:
                return assignment
        return None

    def _safe_relay_waypoint(self, affected_position: GridPosition) -> GridPosition:
        communication_center = self.environment.communication_center
        if communication_center is None:
            communication_center = self.environment.base_position
        path = astar_path(
            self.environment,
            communication_center,
            affected_position,
        )
        if not path.reachable:
            return GridPosition(communication_center.x, communication_center.y)
        safe_waypoint = communication_center
        for position in path.path:
            quality = self.environment.communication_quality_at(position)
            if quality >= self.environment.degraded_communication_threshold:
                safe_waypoint = position
        return GridPosition(safe_waypoint.x, safe_waypoint.y)

    @staticmethod
    def _assignment_snapshot(
        agent: UAVAgentState,
        waypoint: GridPosition,
    ) -> dict[str, Any]:
        return {
            "role": agent.role,
            "assigned_area": agent.assigned_area,
            "objective": agent.current_objective,
            "status": agent.status,
            "waypoint": waypoint.to_dict(),
        }

    def _apply_assignment(
        self,
        agent: UAVAgentState,
        assignment: RoleAssignment,
    ) -> None:
        agent.role = assignment.role
        agent.assigned_area = assignment.assigned_area
        agent.current_objective = assignment.objective
        agent.status = self._status_for_role(assignment.role)

    @staticmethod
    def _store_trigger_event(
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> list[SwarmEvent]:
        for existing in mission_state.memory.events:
            if existing.event_id == event.event_id:
                return []
        stored = deepcopy(event)
        mission_state.memory.add_event(stored)
        return [stored]

    @staticmethod
    def _event_was_replanned(
        event: SwarmEvent,
        mission_state: SwarmMissionState,
    ) -> bool:
        return any(
            memory_event.event_type == "replanning"
            and memory_event.metadata.get("trigger_event_id") == event.event_id
            for memory_event in mission_state.memory.events
        )

    def _select_roles(
        self,
        task: TaskSpec,
        mission_text: str,
        agents: list[UAVAgentState],
    ) -> dict[str, str]:
        roles: dict[str, str] = {}
        eligible: list[UAVAgentState] = []
        for agent in agents:
            if agent.battery_level <= self.environment.low_battery_threshold:
                roles[agent.uav_id] = "returning"
            else:
                eligible.append(agent)

        eligible.sort(
            key=lambda agent: (
                -agent.battery_level,
                -agent.communication_quality,
                agent.uav_id,
            )
        )
        available = list(eligible)

        if self._mission_requires_relay(task, mission_text) and available:
            relay = available.pop(0)
            roles[relay.uav_id] = "relay"

        if self._mission_requires_tracker(task, mission_text) and available:
            tracker = available.pop(0)
            roles[tracker.uav_id] = "tracker"

        if len(eligible) >= 4 and available:
            reserve = available.pop(-1)
            roles[reserve.uav_id] = "reserve"

        for agent in available:
            roles[agent.uav_id] = "scout"
        return roles

    def _build_mission_assignments(
        self,
        task: TaskSpec,
        mission_text: str,
        mission_state: SwarmMissionState,
        roles: dict[str, str],
    ) -> list[RoleAssignment]:
        mission_area = self._mission_area(task, mission_text)
        sector_waypoints = self._sector_waypoints()
        sector_index = 0
        assignments: list[RoleAssignment] = []

        for agent in sorted(mission_state.agents, key=lambda item: item.uav_id):
            role = roles[agent.uav_id]
            target = mission_state.memory.targets[0] if mission_state.memory.targets else None
            if role == "relay":
                area = "communication-relay"
                objective = "Maintain swarm communication relay"
                waypoint = self.environment.communication_center
            elif role == "reserve":
                area = "base-reserve"
                objective = "Hold at base for task handoff"
                waypoint = mission_state.base_position
            elif role == "returning":
                area = "base"
                objective = "Return to base due to battery constraint"
                waypoint = mission_state.base_position
            elif role == "tracker" and target is not None:
                area = target.target_id
                objective = f"Track detected target {target.target_id}"
                waypoint = target.position
            else:
                waypoint = sector_waypoints[sector_index % len(sector_waypoints)]
                sector_index += 1
                area = f"{mission_area}-sector-{sector_index}"
                objective = (
                    "Search priority target sector"
                    if role == "tracker"
                    else "Search assigned sector"
                )

            assignment = self._checked_assignment(
                agent,
                role=role,
                assigned_area=area,
                objective=objective,
                waypoint=waypoint,
            )
            if role in {"scout", "tracker"} and (
                not assignment.path.reachable or not assignment.battery_check.passed
            ):
                fallback_role = (
                    "returning"
                    if agent.battery_level <= self.environment.low_battery_threshold
                    else "reserve"
                )
                assignment = self._checked_assignment(
                    agent,
                    role=fallback_role,
                    assigned_area="base" if fallback_role == "returning" else "base-reserve",
                    objective=(
                        "Return to base due to battery constraint"
                        if fallback_role == "returning"
                        else "Hold at base because remote assignment is infeasible"
                    ),
                    waypoint=mission_state.base_position,
                )
            assignments.append(assignment)
        return assignments

    def _checked_assignment(
        self,
        agent: UAVAgentState,
        *,
        role: str,
        assigned_area: str | None,
        objective: str,
        waypoint: GridPosition,
    ) -> RoleAssignment:
        path = astar_path(self.environment, agent.position, waypoint)
        reserve_battery = 0.0 if role == "returning" else 10.0
        battery_check = check_battery_feasibility(
            agent,
            path,
            self.environment.battery_drain_per_step,
            reserve_battery=reserve_battery,
        )
        communication_check = check_communication_coverage(
            self.environment,
            path,
            min_quality=self.environment.degraded_communication_threshold,
        )
        reason = (
            f"Offline rules assigned {agent.uav_id} as {role}; "
            f"A* path is {path.reason}, battery check "
            f"{'passed' if battery_check.passed else 'failed'}, and communication check "
            f"{'passed' if communication_check.passed else 'failed'}."
        )
        return RoleAssignment(
            uav_id=agent.uav_id,
            role=role,
            assigned_area=assigned_area,
            objective=objective,
            waypoint=GridPosition(waypoint.x, waypoint.y),
            path=path,
            battery_check=battery_check,
            communication_check=communication_check,
            reason=reason,
        )

    def _record_initial_plan(
        self,
        mission_text: str,
        mission_state: SwarmMissionState,
        assignments: list[RoleAssignment],
        timestamp: str,
    ) -> list[SwarmEvent]:
        updates = [
            self._append_event(
                mission_state,
                event_type="mission_started",
                message="Swarm coordinator created the initial mission plan.",
                timestamp=timestamp,
                metadata={"mission_text": mission_text.strip()},
            )
        ]
        agents_by_id = {agent.uav_id: agent for agent in mission_state.agents}
        for assignment in assignments:
            agent = agents_by_id[assignment.uav_id]
            agent.role = assignment.role
            agent.assigned_area = assignment.assigned_area
            agent.current_objective = assignment.objective
            agent.status = self._status_for_role(assignment.role)
            event = self._append_event(
                mission_state,
                event_type="area_assigned",
                message=(
                    f"{assignment.uav_id} assigned as {assignment.role} "
                    f"for {assignment.assigned_area}."
                ),
                timestamp=timestamp,
                uav_id=assignment.uav_id,
                area_id=assignment.assigned_area,
                metadata={
                    "role": assignment.role,
                    "objective": assignment.objective,
                    "waypoint": assignment.waypoint.to_dict(),
                    "algorithm_checks": assignment.algorithm_checks_to_dict(),
                },
            )
            agent.memory_refs.append(event.event_id)
            updates.append(event)
        return updates

    def _append_event(
        self,
        mission_state: SwarmMissionState,
        *,
        event_type: str,
        message: str,
        timestamp: str,
        uav_id: str | None = None,
        target_id: str | None = None,
        area_id: str | None = None,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> SwarmEvent:
        event = SwarmEvent(
            event_id=self._next_event_id(mission_state),
            event_type=event_type,
            message=message,
            timestamp=timestamp,
            uav_id=uav_id,
            target_id=target_id,
            area_id=area_id,
            severity=severity,
            metadata=metadata or {},
        )
        return mission_state.memory.add_event(event)

    @staticmethod
    def _next_event_id(mission_state: SwarmMissionState) -> str:
        existing_ids = {event.event_id for event in mission_state.memory.events}
        sequence = len(existing_ids) + 1
        while True:
            candidate = f"{mission_state.mission_id}-evt-{sequence:03d}"
            if candidate not in existing_ids:
                return candidate
            sequence += 1

    def _sector_waypoints(self) -> list[GridPosition]:
        candidates = [
            GridPosition(self.environment.width // 2, self.environment.height // 4),
            GridPosition(self.environment.width // 2, self.environment.height // 2),
            GridPosition(self.environment.width // 4, self.environment.height // 2),
            GridPosition(self.environment.width // 4, self.environment.height // 4),
        ]
        waypoints = [self._nearest_open_position(candidate) for candidate in candidates]
        return waypoints or [self.environment.base_position]

    def _nearest_open_position(self, preferred: GridPosition) -> GridPosition:
        if not self.environment.is_blocked(preferred):
            return preferred
        for radius in range(1, max(self.environment.width, self.environment.height)):
            for dx, dy in ((radius, 0), (0, radius), (-radius, 0), (0, -radius)):
                candidate = GridPosition(preferred.x + dx, preferred.y + dy)
                if not self.environment.is_blocked(candidate):
                    return candidate
        return self.environment.base_position

    @staticmethod
    def _mission_requires_relay(task: TaskSpec, mission_text: str) -> bool:
        lowered = mission_text.lower()
        return (
            "中继" in mission_text
            or "relay" in lowered
            or "low_bandwidth_coordination" in task.constraints
        )

    @staticmethod
    def _mission_requires_tracker(task: TaskSpec, mission_text: str) -> bool:
        lowered = mission_text.lower()
        return (
            "目标" in mission_text
            or "热源" in mission_text
            or "target" in lowered
            or "target_tracking" in task.objectives
        )

    @staticmethod
    def _mission_area(task: TaskSpec, mission_text: str) -> str:
        if task.search_areas:
            return task.search_areas[0]
        match = re.search(r"((?:山区|区域)\s*[0-9A-Za-z_-]+)", mission_text)
        if match:
            return match.group(1).replace(" ", "")
        return "mission-area"

    @staticmethod
    def _status_for_role(role: str) -> str:
        return {
            "relay": "holding",
            "reserve": "standby",
            "returning": "returning",
        }.get(role, "assigned")

    @staticmethod
    def _offline_plan_rationale(assignments: list[RoleAssignment]) -> str:
        feasible_count = sum(assignment.feasible for assignment in assignments)
        role_summary = ", ".join(
            f"{assignment.uav_id}={assignment.role}" for assignment in assignments
        )
        return (
            "Offline rules produced deterministic role assignments and validated every "
            f"route with A*, battery, and communication checks. {feasible_count}/"
            f"{len(assignments)} assignments passed all checks: {role_summary}."
        )
