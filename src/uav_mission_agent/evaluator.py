from __future__ import annotations

from .models import EvaluationResult, MissionScenario


def evaluate_plan(plan: dict, scenario: MissionScenario) -> EvaluationResult:
    expected = scenario.expected
    mission_config = plan.get("mission_config", {})
    task = plan.get("task", {})
    risks = plan.get("risks", [])
    recommendations = plan.get("recommendations", [])

    breakdown = {
        "uav_count": _score_exact(mission_config.get("uav_count"), expected["uav_count"]),
        "search_areas": _score_list(mission_config.get("search_areas", []), expected["search_areas"]),
        "avoid_zones": _score_list(mission_config.get("avoid_zones", []), expected["avoid_zones"]),
        "objectives": _score_list(task.get("objectives", []), expected["objectives"]),
        "constraints": _score_list(mission_config.get("constraints", []), expected["constraints"]),
        "risk_keywords": _score_keywords(risks + recommendations, expected["risk_keywords"]),
    }
    missing = _missing_requirements(plan, scenario)
    score = round(sum(breakdown.values()) / len(breakdown), 3)
    return EvaluationResult(
        scenario_id=scenario.scenario_id,
        score=score,
        breakdown=breakdown,
        missing_requirements=missing,
    )


def _score_exact(actual: object, expected: object) -> float:
    return 1.0 if actual == expected else 0.0


def _score_list(actual: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    actual_set = set(actual)
    expected_set = set(expected)
    return round(len(actual_set & expected_set) / len(expected_set), 3)


def _score_keywords(text_items: list[str], expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    text = " ".join(text_items)
    matched = sum(1 for keyword in expected_keywords if keyword in text)
    return round(matched / len(expected_keywords), 3)


def _missing_requirements(plan: dict, scenario: MissionScenario) -> list[str]:
    expected = scenario.expected
    mission_config = plan.get("mission_config", {})
    task = plan.get("task", {})
    risks = plan.get("risks", [])
    recommendations = plan.get("recommendations", [])

    missing: list[str] = []
    if mission_config.get("uav_count") != expected["uav_count"]:
        missing.append("uav_count")
    missing.extend(_missing_from_list(mission_config.get("search_areas", []), expected["search_areas"]))
    missing.extend(_missing_from_list(mission_config.get("avoid_zones", []), expected["avoid_zones"]))
    missing.extend(_missing_from_list(task.get("objectives", []), expected["objectives"]))
    missing.extend(_missing_from_list(mission_config.get("constraints", []), expected["constraints"]))

    risk_text = " ".join(risks + recommendations)
    for keyword in expected["risk_keywords"]:
        if keyword not in risk_text:
            missing.append(keyword)
    return missing


def _missing_from_list(actual: list[str], expected: list[str]) -> list[str]:
    actual_set = set(actual)
    return [item for item in expected if item not in actual_set]

