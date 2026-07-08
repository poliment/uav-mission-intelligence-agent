from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import MissionScenario


REQUIRED_FIELDS = ("id", "name", "difficulty", "mission_text", "expected")
EXPECTED_FIELDS = (
    "uav_count",
    "search_areas",
    "avoid_zones",
    "objectives",
    "constraints",
    "risk_keywords",
)


def load_scenario(path: str | Path) -> MissionScenario:
    scenario_path = Path(path)
    data = json.loads(scenario_path.read_text(encoding="utf-8"))
    _validate_scenario(data, scenario_path)
    return MissionScenario(
        scenario_id=data["id"],
        name=data["name"],
        difficulty=data["difficulty"],
        mission_text=data["mission_text"],
        expected=data["expected"],
    )


def load_scenarios(directory: str | Path) -> list[MissionScenario]:
    scenario_dir = Path(directory)
    scenarios: list[MissionScenario] = []
    for path in sorted(scenario_dir.glob("*.json")):
        try:
            scenarios.append(load_scenario(path))
        except ValueError:
            continue
    return scenarios


def _validate_scenario(data: dict[str, Any], path: Path) -> None:
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"{path} missing required field: {field}")

    expected = data["expected"]
    if not isinstance(expected, dict):
        raise ValueError(f"{path} expected must be an object")

    for field in EXPECTED_FIELDS:
        if field not in expected:
            raise ValueError(f"{path} missing expected field: {field}")

