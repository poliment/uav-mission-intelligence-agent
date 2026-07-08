from __future__ import annotations

from collections.abc import Iterable

from .evaluator import evaluate_plan
from .models import MissionScenario
from .workflow import run_mission_workflow


def run_benchmark(scenarios: Iterable[MissionScenario]) -> dict:
    scenario_list = list(scenarios)
    results = []
    for scenario in scenario_list:
        plan = run_mission_workflow(scenario.mission_text)
        evaluation = evaluate_plan(plan, scenario)
        result = evaluation.to_dict()
        result["difficulty"] = scenario.difficulty
        result["name"] = scenario.name
        results.append(result)

    average_score = round(
        sum(result["score"] for result in results) / len(results),
        3,
    ) if results else 0.0
    return {
        "summary": {
            "total_scenarios": len(results),
            "average_score": average_score,
            "passed_scenarios": sum(1 for result in results if result["score"] >= 0.8),
        },
        "results": results,
    }

