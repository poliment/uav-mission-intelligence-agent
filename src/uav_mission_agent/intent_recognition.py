from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .trajectory import TrajectoryPoint, TrajectorySummary, summarize_trajectory


@dataclass
class IntentRecognitionResult:
    intent: str
    confidence: float
    summary: TrajectorySummary
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["summary"] = self.summary.to_dict()
        return data


def recognize_intent(points: list[TrajectoryPoint]) -> IntentRecognitionResult:
    summary = summarize_trajectory(points)
    if summary.altitude_trend == "descending" and summary.speed_trend == "decelerating":
        return IntentRecognitionResult(
            intent="return_to_base",
            confidence=0.82,
            summary=summary,
            evidence=[
                "descending altitude with decelerating speed",
                "trajectory is consistent with recovery or return-to-base behavior",
            ],
        )
    if summary.heading_change_degrees >= 250 and summary.displacement_meters < 80:
        return IntentRecognitionResult(
            intent="loitering",
            confidence=0.76,
            summary=summary,
            evidence=[
                "high heading change with low displacement",
                "aircraft remains near the same local area",
            ],
        )
    if summary.point_count >= 5 and summary.heading_change_degrees >= 240:
        return IntentRecognitionResult(
            intent="area_search",
            confidence=0.72,
            summary=summary,
            evidence=[
                "multi-turn coverage-style trajectory",
                "heading changes indicate sweep or lawnmower-like search behavior",
            ],
        )
    if summary.speed_trend == "steady" and 45 <= summary.heading_change_degrees <= 220:
        return IntentRecognitionResult(
            intent="target_tracking",
            confidence=0.64,
            summary=summary,
            evidence=[
                "steady speed with moderate heading changes",
                "trajectory is consistent with maintaining observation of a moving target",
            ],
        )
    return IntentRecognitionResult(
        intent="transit",
        confidence=0.55,
        summary=summary,
        evidence=[
            "limited maneuvering evidence",
            "trajectory is most consistent with point-to-point transit",
        ],
    )
