from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class TaskSpec:
    raw_request: str
    drone_count: int
    search_areas: list[str]
    avoid_zones: list[str]
    objectives: list[str]
    constraints: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeSnippet:
    topic: str
    content: str
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MissionPlan:
    task: TaskSpec
    retrieved_knowledge: list[KnowledgeSnippet]
    recommendations: list[str]
    risks: list[str]
    mission_config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task.to_dict(),
            "retrieved_knowledge": [snippet.to_dict() for snippet in self.retrieved_knowledge],
            "recommendations": self.recommendations,
            "risks": self.risks,
            "mission_config": self.mission_config,
        }


@dataclass
class MissionScenario:
    scenario_id: str
    name: str
    difficulty: str
    mission_text: str
    expected: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    scenario_id: str
    score: float
    breakdown: dict[str, float]
    missing_requirements: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
