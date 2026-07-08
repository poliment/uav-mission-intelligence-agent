from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


REQUIRED_POINT_FIELDS = (
    "timestamp",
    "latitude",
    "longitude",
    "altitude",
    "speed",
    "heading",
    "roll",
    "pitch",
    "yaw",
)


@dataclass
class TrajectoryPoint:
    timestamp: float
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float
    roll: float
    pitch: float
    yaw: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectorySummary:
    point_count: int
    duration_seconds: float
    mean_altitude: float
    mean_speed: float
    altitude_trend: str
    speed_trend: str
    heading_change_degrees: float
    displacement_meters: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_trajectory_points(data: list[dict[str, Any]]) -> list[TrajectoryPoint]:
    if not isinstance(data, list):
        raise ValueError("trajectory data must be a list of point objects")
    points = [_load_point(item, index) for index, item in enumerate(data)]
    if not points:
        raise ValueError("trajectory data must contain at least one point")
    return sorted(points, key=lambda point: point.timestamp)


def summarize_trajectory(points: list[TrajectoryPoint]) -> TrajectorySummary:
    if not points:
        raise ValueError("trajectory summary requires at least one point")
    ordered = sorted(points, key=lambda point: point.timestamp)
    first = ordered[0]
    last = ordered[-1]
    mean_altitude = sum(point.altitude for point in ordered) / len(ordered)
    mean_speed = sum(point.speed for point in ordered) / len(ordered)
    return TrajectorySummary(
        point_count=len(ordered),
        duration_seconds=last.timestamp - first.timestamp,
        mean_altitude=mean_altitude,
        mean_speed=mean_speed,
        altitude_trend=_trend(last.altitude - first.altitude, positive="climbing", negative="descending", neutral="level"),
        speed_trend=_trend(last.speed - first.speed, positive="accelerating", negative="decelerating", neutral="steady"),
        heading_change_degrees=_heading_change(ordered),
        displacement_meters=_haversine_meters(first.latitude, first.longitude, last.latitude, last.longitude),
    )


def _load_point(item: dict[str, Any], index: int) -> TrajectoryPoint:
    if not isinstance(item, dict):
        raise ValueError(f"trajectory point {index} must be an object")
    for field in REQUIRED_POINT_FIELDS:
        if field not in item:
            raise ValueError(f"trajectory point {index} missing required field: {field}")
    try:
        values = {field: float(item[field]) for field in REQUIRED_POINT_FIELDS}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"trajectory point {index} contains a non-numeric field") from exc
    return TrajectoryPoint(**values)


def _trend(delta: float, *, positive: str, negative: str, neutral: str) -> str:
    if delta > 1.0:
        return positive
    if delta < -1.0:
        return negative
    return neutral


def _heading_change(points: list[TrajectoryPoint]) -> float:
    total = 0.0
    for previous, current in zip(points, points[1:]):
        total += abs(_angle_delta(previous.heading, current.heading))
    return round(total, 3)


def _angle_delta(source: float, target: float) -> float:
    return (target - source + 180.0) % 360.0 - 180.0


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_meters = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    return round(radius_meters * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)), 3)
