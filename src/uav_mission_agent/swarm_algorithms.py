from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any

from .swarm_environment import SwarmGridEnvironment
from .swarm_models import DetectedTarget, GridPosition, UAVAgentState


@dataclass
class AStarPathResult:
    start: GridPosition
    goal: GridPosition
    path: list[GridPosition]
    distance: int | None
    reachable: bool
    reason: str
    explored_nodes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": "astar",
            "start": self.start.to_dict(),
            "goal": self.goal.to_dict(),
            "path": [position.to_dict() for position in self.path],
            "distance": self.distance,
            "reachable": self.reachable,
            "reason": self.reason,
            "explored_nodes": self.explored_nodes,
        }


@dataclass
class ConstraintCheck:
    name: str
    passed: bool
    summary: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class CandidateScore:
    uav_id: str
    target_id: str
    score: float
    path: AStarPathResult
    battery_check: ConstraintCheck
    communication_check: ConstraintCheck
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "uav_id": self.uav_id,
            "target_id": self.target_id,
            "score": self.score,
            "path": self.path.to_dict(),
            "battery_check": self.battery_check.to_dict(),
            "communication_check": self.communication_check.to_dict(),
            "explanation": self.explanation,
        }


@dataclass
class TargetAssignment:
    target_id: str
    uav_id: str | None
    score: float
    path: AStarPathResult | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "uav_id": self.uav_id,
            "score": self.score,
            "path": self.path.to_dict() if self.path else None,
            "reason": self.reason,
        }


def astar_path(
    environment: SwarmGridEnvironment,
    start: GridPosition,
    goal: GridPosition,
) -> AStarPathResult:
    if environment.is_blocked(start):
        return AStarPathResult(start, goal, [], None, False, "start_blocked", 0)
    if environment.is_blocked(goal):
        return AStarPathResult(start, goal, [], None, False, "goal_blocked", 0)
    if _position_key(start) == _position_key(goal):
        return AStarPathResult(start, goal, [GridPosition(start.x, start.y)], 0, True, "path_found", 1)

    open_heap: list[tuple[int, int, int, int, tuple[int, int]]] = []
    start_key = _position_key(start)
    goal_key = _position_key(goal)
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], int] = {start_key: 0}
    start_h = _manhattan(start_key, goal_key)
    heapq.heappush(open_heap, (start_h, start_h, start.x, start.y, start_key))
    explored: set[tuple[int, int]] = set()

    while open_heap:
        _, _, _, _, current_key = heapq.heappop(open_heap)
        if current_key in explored:
            continue
        explored.add(current_key)
        if current_key == goal_key:
            path = _reconstruct_path(came_from, current_key)
            return AStarPathResult(
                start=start,
                goal=goal,
                path=path,
                distance=len(path) - 1,
                reachable=True,
                reason="path_found",
                explored_nodes=len(explored),
            )

        current_cost = g_score[current_key]
        for neighbor in _neighbors(current_key):
            neighbor_position = GridPosition(neighbor[0], neighbor[1])
            if environment.is_blocked(neighbor_position):
                continue
            tentative_g = current_cost + 1
            if tentative_g >= g_score.get(neighbor, 1_000_000_000):
                continue
            came_from[neighbor] = current_key
            g_score[neighbor] = tentative_g
            h_score = _manhattan(neighbor, goal_key)
            f_score = tentative_g + h_score
            heapq.heappush(open_heap, (f_score, h_score, neighbor[0], neighbor[1], neighbor))

    return AStarPathResult(start, goal, [], None, False, "no_path", len(explored))


def check_battery_feasibility(
    agent: UAVAgentState,
    path: AStarPathResult,
    battery_per_step: float,
    reserve_battery: float = 10.0,
) -> ConstraintCheck:
    if not path.reachable or path.distance is None:
        return ConstraintCheck(
            name="battery_feasibility",
            passed=False,
            summary="battery check failed because A* path is unreachable",
            details={
                "uav_id": agent.uav_id,
                "reachable": False,
                "battery_level": agent.battery_level,
                "required_battery": None,
                "remaining_after_path": None,
                "reserve_battery": reserve_battery,
            },
        )

    travel_battery = round(path.distance * battery_per_step, 3)
    required_battery = round(travel_battery + reserve_battery, 3)
    remaining_after_path = round(agent.battery_level - travel_battery, 3)
    passed = agent.battery_level >= required_battery
    summary = (
        "battery check passed with reserve"
        if passed
        else "battery check failed: reserve would be violated"
    )
    return ConstraintCheck(
        name="battery_feasibility",
        passed=passed,
        summary=summary,
        details={
            "uav_id": agent.uav_id,
            "reachable": True,
            "path_distance": path.distance,
            "battery_per_step": battery_per_step,
            "battery_level": agent.battery_level,
            "travel_battery": travel_battery,
            "required_battery": required_battery,
            "remaining_after_path": remaining_after_path,
            "reserve_battery": reserve_battery,
        },
    )


def check_communication_coverage(
    environment: SwarmGridEnvironment,
    path: AStarPathResult,
    min_quality: float = 0.35,
) -> ConstraintCheck:
    if not path.reachable:
        return ConstraintCheck(
            name="communication_coverage",
            passed=False,
            summary="communication check failed because A* path is unreachable",
            details={
                "minimum_quality": None,
                "required_quality": min_quality,
                "weak_points": [],
            },
        )

    qualities = [
        (position, environment.communication_quality_at(position))
        for position in path.path
    ]
    minimum_quality = min((quality for _, quality in qualities), default=0.0)
    weak_points = [
        position.to_dict()
        for position, quality in qualities
        if quality < min_quality
    ]
    passed = not weak_points
    summary = (
        "communication coverage check passed"
        if passed
        else "communication coverage check failed: weak points on A* path"
    )
    return ConstraintCheck(
        name="communication_coverage",
        passed=passed,
        summary=summary,
        details={
            "minimum_quality": minimum_quality,
            "required_quality": min_quality,
            "weak_points": weak_points,
        },
    )


def score_candidate_for_target(
    agent: UAVAgentState,
    target: DetectedTarget,
    environment: SwarmGridEnvironment,
    *,
    battery_per_step: float | None = None,
    reserve_battery: float = 10.0,
    min_comm_quality: float = 0.35,
) -> CandidateScore:
    step_cost = environment.battery_drain_per_step if battery_per_step is None else battery_per_step
    path = astar_path(environment, agent.position, target.position)
    battery_check = check_battery_feasibility(agent, path, step_cost, reserve_battery)
    communication_check = check_communication_coverage(environment, path, min_comm_quality)
    score = _candidate_score(agent, path, battery_check, communication_check)
    explanation = _candidate_explanation(agent, target, path, battery_check, communication_check)
    return CandidateScore(
        uav_id=agent.uav_id,
        target_id=target.target_id,
        score=score,
        path=path,
        battery_check=battery_check,
        communication_check=communication_check,
        explanation=explanation,
    )


def assign_targets_to_uavs(
    agents: list[UAVAgentState],
    targets: list[DetectedTarget],
    environment: SwarmGridEnvironment,
    *,
    battery_per_step: float | None = None,
    reserve_battery: float = 10.0,
    min_comm_quality: float = 0.35,
) -> list[TargetAssignment]:
    assignments: list[TargetAssignment] = []
    assigned_uavs: set[str] = set()
    for target in targets:
        candidates = [
            score_candidate_for_target(
                agent,
                target,
                environment,
                battery_per_step=battery_per_step,
                reserve_battery=reserve_battery,
                min_comm_quality=min_comm_quality,
            )
            for agent in agents
            if agent.uav_id not in assigned_uavs
        ]
        if not candidates:
            assignments.append(
                TargetAssignment(
                    target_id=target.target_id,
                    uav_id=None,
                    score=0.0,
                    path=None,
                    reason="unassigned: no available UAV candidate",
                )
            )
            continue
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.uav_id))
        best = candidates[0]
        if best.uav_id is not None:
            assigned_uavs.add(best.uav_id)
        assignments.append(
            TargetAssignment(
                target_id=target.target_id,
                uav_id=best.uav_id,
                score=best.score,
                path=best.path,
                reason=f"assigned {target.target_id} to {best.uav_id}: {best.explanation}",
            )
        )
    return assignments


def _candidate_score(
    agent: UAVAgentState,
    path: AStarPathResult,
    battery_check: ConstraintCheck,
    communication_check: ConstraintCheck,
) -> float:
    if not path.reachable or path.distance is None:
        return 0.0
    score = 100.0 - (path.distance * 5.0)
    if not battery_check.passed:
        score -= 35.0
    if not communication_check.passed:
        score -= 20.0
    if agent.role == "relay" and communication_check.passed:
        score += 5.0
    return round(max(0.0, score), 3)


def _candidate_explanation(
    agent: UAVAgentState,
    target: DetectedTarget,
    path: AStarPathResult,
    battery_check: ConstraintCheck,
    communication_check: ConstraintCheck,
) -> str:
    if not path.reachable:
        return f"A* could not find a safe path from {agent.uav_id} to {target.target_id}"
    return (
        f"A* path distance {path.distance}; "
        f"battery {'ok' if battery_check.passed else 'insufficient'}; "
        f"communication {'covered' if communication_check.passed else 'weak'}"
    )


def _neighbors(position: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = position
    return [
        (x + 1, y),
        (x, y + 1),
        (x - 1, y),
        (x, y - 1),
    ]


def _position_key(position: GridPosition) -> tuple[int, int]:
    return (position.x, position.y)


def _manhattan(start: tuple[int, int], goal: tuple[int, int]) -> int:
    return abs(start[0] - goal[0]) + abs(start[1] - goal[1])


def _reconstruct_path(
    came_from: dict[tuple[int, int], tuple[int, int]],
    current: tuple[int, int],
) -> list[GridPosition]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return [GridPosition(x, y) for x, y in path]
