from __future__ import annotations

from typing import Any


SCHEMA_NAME = "uav_mission_plan"
SCHEMA_VERSION = "1.0"

MISSION_PLAN_SCHEMA: dict[str, Any] = {
    "schema_name": SCHEMA_NAME,
    "schema_version": SCHEMA_VERSION,
    "type": "object",
    "required": [
        "task",
        "retrieved_knowledge",
        "recommendations",
        "risks",
        "mission_config",
    ],
    "properties": {
        "task": {
            "type": "object",
            "required": [
                "raw_request",
                "drone_count",
                "search_areas",
                "avoid_zones",
                "objectives",
                "constraints",
            ],
        },
        "retrieved_knowledge": {"type": "array"},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "mission_config": {
            "type": "object",
            "required": [
                "version",
                "uav_count",
                "search_areas",
                "avoid_zones",
                "objectives",
                "constraints",
                "coordination_mode",
                "planning_policy",
            ],
        },
    },
}


def build_schema_output(plan: dict[str, Any]) -> dict[str, Any]:
    validation = validate_mission_plan(plan)
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "schema": MISSION_PLAN_SCHEMA,
        "validation": validation,
        "data": plan,
    }


def validate_mission_plan(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for field in MISSION_PLAN_SCHEMA["required"]:
        if field not in plan:
            errors.append(f"missing required field: {field}")

    _expect_dict(plan, "task", errors)
    _expect_list(plan, "retrieved_knowledge", errors)
    _expect_list(plan, "recommendations", errors)
    _expect_list(plan, "risks", errors)
    _expect_dict(plan, "mission_config", errors)

    task = plan.get("task")
    if isinstance(task, dict):
        for field in MISSION_PLAN_SCHEMA["properties"]["task"]["required"]:
            if field not in task:
                errors.append(f"missing task field: {field}")
        _expect_type(task, "raw_request", str, errors, "task")
        _expect_type(task, "drone_count", int, errors, "task")
        for field in ("search_areas", "avoid_zones", "objectives", "constraints"):
            _expect_list(task, field, errors, prefix="task")

    mission_config = plan.get("mission_config")
    if isinstance(mission_config, dict):
        for field in MISSION_PLAN_SCHEMA["properties"]["mission_config"]["required"]:
            if field not in mission_config:
                errors.append(f"missing mission_config field: {field}")
        _expect_type(mission_config, "uav_count", int, errors, "mission_config")
        for field in ("search_areas", "avoid_zones", "objectives", "constraints"):
            _expect_list(mission_config, field, errors, prefix="mission_config")
        for field in ("coordination_mode", "planning_policy"):
            _expect_type(mission_config, field, str, errors, "mission_config")

    _expect_string_list(plan, "recommendations", errors)
    _expect_string_list(plan, "risks", errors)

    return {
        "valid": not errors,
        "errors": errors,
    }


def _expect_dict(data: dict[str, Any], field: str, errors: list[str], prefix: str | None = None) -> None:
    value = data.get(field)
    if field in data and not isinstance(value, dict):
        errors.append(f"{_label(prefix, field)} must be an object")


def _expect_list(data: dict[str, Any], field: str, errors: list[str], prefix: str | None = None) -> None:
    value = data.get(field)
    if field in data and not isinstance(value, list):
        errors.append(f"{_label(prefix, field)} must be an array")


def _expect_type(
    data: dict[str, Any],
    field: str,
    expected_type: type,
    errors: list[str],
    prefix: str | None = None,
) -> None:
    value = data.get(field)
    if field in data and not isinstance(value, expected_type):
        errors.append(f"{_label(prefix, field)} must be {expected_type.__name__}")


def _expect_string_list(data: dict[str, Any], field: str, errors: list[str]) -> None:
    value = data.get(field)
    if not isinstance(value, list):
        return
    if any(not isinstance(item, str) for item in value):
        errors.append(f"{field} must contain only strings")


def _label(prefix: str | None, field: str) -> str:
    return f"{prefix}.{field}" if prefix else field
