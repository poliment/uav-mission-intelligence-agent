from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .costing import ProviderPricing, default_pricing_for, estimate_cost, normalize_token_usage
from .evaluator import evaluate_plan
from .llm_provider import LLMProvider, build_llm_provider
from .models import MissionScenario
from .workflow import run_mission_workflow


ProviderFactory = Callable[..., LLMProvider | None]
WorkflowRunner = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class BenchmarkProviderConfig:
    label: str
    provider_name: str = "offline"
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = None
    pricing: ProviderPricing | None = None


def run_benchmark_v2(
    scenarios: Iterable[MissionScenario],
    *,
    provider_configs: Iterable[BenchmarkProviderConfig] | None = None,
    graph_backend: str = "rule-based",
    provider_factory: ProviderFactory = build_llm_provider,
    workflow_runner: WorkflowRunner = run_mission_workflow,
) -> dict[str, Any]:
    scenario_list = list(scenarios)
    configs = list(provider_configs or [BenchmarkProviderConfig(label="offline")])

    results = []
    for config in configs:
        llm_provider = _build_provider(config, provider_factory)
        provider_name = _provider_name(config, llm_provider)
        model = _provider_model(config, llm_provider)
        pricing = config.pricing or default_pricing_for(provider_name, model)
        for scenario in scenario_list:
            results.append(
                _run_single_scenario(
                    scenario=scenario,
                    config=config,
                    provider_name=provider_name,
                    model=model,
                    pricing=pricing,
                    llm_provider=llm_provider,
                    graph_backend=graph_backend,
                    workflow_runner=workflow_runner,
                )
            )

    return {
        "summary": _build_summary(results, scenario_list, configs),
        "provider_comparison": _group_provider_summary(results),
        "difficulty_summary": _group_difficulty_summary(results),
        "results": results,
    }


def provider_configs_from_names(
    provider_names: str | Iterable[str] | None,
    *,
    pricing: Iterable[ProviderPricing] | None = None,
) -> list[BenchmarkProviderConfig]:
    names = _split_provider_names(provider_names)
    pricing_by_key = {
        (_normalize_name(item.provider_name), item.model): item
        for item in pricing or []
    }
    configs: list[BenchmarkProviderConfig] = []
    for name in names:
        normalized, model = _provider_and_model_from_name(name)
        model = model or _default_model_for_provider(normalized)
        configs.append(
            BenchmarkProviderConfig(
                label=_provider_label(normalized, model),
                provider_name=normalized,
                model=model,
                pricing=pricing_by_key.get((normalized, model)),
            )
        )
    return configs


def _provider_and_model_from_name(name: str) -> tuple[str, str | None]:
    raw = name.strip()
    if "/" in raw:
        provider_name, model = raw.split("/", 1)
        return _normalize_name(provider_name), model.strip() or None
    return _normalize_name(raw), None


def _run_single_scenario(
    *,
    scenario: MissionScenario,
    config: BenchmarkProviderConfig,
    provider_name: str,
    model: str | None,
    pricing: ProviderPricing,
    llm_provider: LLMProvider | None,
    graph_backend: str,
    workflow_runner: WorkflowRunner,
) -> dict[str, Any]:
    start = perf_counter()
    plan = workflow_runner(
        scenario.mission_text,
        llm_provider=llm_provider,
        graph_backend=graph_backend,
    )
    latency_ms = round((perf_counter() - start) * 1000, 3)
    evaluation = evaluate_plan(plan, scenario).to_dict()
    usage = _extract_usage(plan, llm_provider)
    cost = estimate_cost(usage, pricing)
    schema_validation = plan.get("schema_validation", {})

    return {
        "run_id": f"{config.label}:{scenario.scenario_id}",
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "difficulty": scenario.difficulty,
        "provider_label": config.label,
        "provider_name": provider_name,
        "model": model,
        "graph_backend": graph_backend,
        "status": "completed",
        "score": evaluation["score"],
        "breakdown": evaluation["breakdown"],
        "missing_requirements": evaluation["missing_requirements"],
        "schema_valid": bool(schema_validation.get("valid", True)),
        "latency_ms": latency_ms,
        "token_usage": usage,
        "estimated_cost": cost,
    }


def _build_provider(config: BenchmarkProviderConfig, provider_factory: ProviderFactory) -> LLMProvider | None:
    if _is_offline_provider(config.provider_name):
        return None
    return provider_factory(
        config.provider_name,
        api_key_env=config.api_key_env,
        model=config.model,
        base_url=config.base_url,
    )


def _extract_usage(plan: dict[str, Any], llm_provider: LLMProvider | None) -> dict[str, int]:
    plan_usage = plan.get("llm_metadata", {}).get("usage")
    if plan_usage:
        return normalize_token_usage(plan_usage)
    provider_usage = getattr(llm_provider, "last_usage", None)
    return normalize_token_usage(provider_usage)


def _build_summary(
    results: list[dict[str, Any]],
    scenarios: list[MissionScenario],
    configs: list[BenchmarkProviderConfig],
) -> dict[str, Any]:
    return {
        "benchmark_version": "2.0",
        "total_scenarios": len(scenarios),
        "provider_count": len(configs),
        "total_runs": len(results),
        "average_score": _average(result["score"] for result in results),
        "passed_runs": sum(1 for result in results if result["score"] >= 0.8),
        "average_latency_ms": _average(result["latency_ms"] for result in results),
        "estimated_total_cost": _sum_cost(results),
        "currency": _first_currency(results),
    }


def _group_provider_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["provider_label"]].append(result)

    summary = []
    for provider_label in sorted(grouped):
        rows = grouped[provider_label]
        first = rows[0]
        summary.append(
            {
                "provider_label": provider_label,
                "provider_name": first["provider_name"],
                "model": first["model"],
                "run_count": len(rows),
                "average_score": _average(row["score"] for row in rows),
                "passed_runs": sum(1 for row in rows if row["score"] >= 0.8),
                "average_latency_ms": _average(row["latency_ms"] for row in rows),
                "estimated_total_cost": _sum_cost(rows),
                "currency": _first_currency(rows),
            }
        )
    return summary


def _group_difficulty_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["difficulty"]].append(result)

    summary = []
    for difficulty in sorted(grouped):
        rows = grouped[difficulty]
        summary.append(
            {
                "difficulty": difficulty,
                "run_count": len(rows),
                "average_score": _average(row["score"] for row in rows),
                "passed_runs": sum(1 for row in rows if row["score"] >= 0.8),
            }
        )
    return summary


def _average(values: Iterable[float]) -> float:
    numbers = list(values)
    if not numbers:
        return 0.0
    return round(sum(numbers) / len(numbers), 3)


def _sum_cost(results: list[dict[str, Any]]) -> float:
    return round(sum(result["estimated_cost"]["total_cost"] for result in results), 8)


def _first_currency(results: list[dict[str, Any]]) -> str:
    for result in results:
        currency = result.get("estimated_cost", {}).get("currency")
        if currency:
            return currency
    return "USD"


def _provider_name(config: BenchmarkProviderConfig, llm_provider: LLMProvider | None) -> str:
    if llm_provider is not None:
        return llm_provider.provider_name
    if _is_offline_provider(config.provider_name):
        return "offline"
    return config.provider_name


def _provider_model(config: BenchmarkProviderConfig, llm_provider: LLMProvider | None) -> str | None:
    if llm_provider is not None:
        return llm_provider.model
    if _is_offline_provider(config.provider_name):
        return "rule-based"
    return config.model


def _is_offline_provider(provider_name: str | None) -> bool:
    return _normalize_name(provider_name) in {"none", "offline", "rule-based"}


def _split_provider_names(provider_names: str | Iterable[str] | None) -> list[str]:
    if provider_names is None:
        return ["offline"]
    if isinstance(provider_names, str):
        names = [item.strip() for item in provider_names.split(",") if item.strip()]
        return names or ["offline"]
    return [item.strip() for item in provider_names if item.strip()] or ["offline"]


def _normalize_name(name: str | None) -> str:
    return (name or "offline").strip().lower()


def _default_model_for_provider(provider_name: str) -> str | None:
    if provider_name == "deepseek":
        return "deepseek-v4-flash"
    if provider_name in {"openai-compatible", "openai"}:
        return "gpt-4o-mini"
    if _is_offline_provider(provider_name):
        return "rule-based"
    return None


def _provider_label(provider_name: str, model: str | None) -> str:
    if _is_offline_provider(provider_name):
        return "offline"
    return f"{provider_name}:{model}" if model else provider_name
