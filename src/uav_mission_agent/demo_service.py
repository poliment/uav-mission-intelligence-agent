from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
from typing import Any

from .agent_graph import run_agent_workflow
from .benchmark_v2 import run_benchmark_v2
from .dashboard import DEFAULT_SCENARIO_DIR
from .llm_provider import LLMProviderError, build_llm_provider
from .mission_visualization import render_mission_execution_svg
from .scenario_loader import load_scenarios


SUPPORTED_PROVIDERS = {"offline", "deepseek", "openai-compatible"}
DEFAULT_BENCHMARK_REPORT = Path("results") / "deepseek_provider_comparison_2026-07-09.json"


class DemoError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


def build_mission_demo_payload(
    mission_text: str,
    provider: str = "offline",
    model: str | None = None,
    base_url: str | None = None,
    provider_factory: Callable = build_llm_provider,
    workflow_runner: Callable = run_agent_workflow,
) -> dict[str, Any]:
    cleaned_mission = mission_text.strip()
    if not cleaned_mission:
        raise DemoError(400, "invalid_mission", "mission text is required")

    provider_name = _normalize_provider(provider)
    llm_provider = _build_demo_provider(
        provider_name=provider_name,
        model=_blank_to_none(model),
        base_url=_blank_to_none(base_url),
        provider_factory=provider_factory,
    )
    try:
        plan = workflow_runner(cleaned_mission, llm_provider=llm_provider)
    except LLMProviderError as exc:
        raise DemoError(400, "provider_error", _safe_message(str(exc))) from exc

    metadata = plan.get("llm_metadata", {})
    provider_model = metadata.get("model") or getattr(llm_provider, "model", None) or (
        "rule-based" if provider_name == "offline" else model
    )
    return {
        "status": "ok",
        "mission_text": cleaned_mission,
        "provider": {
            "name": provider_name,
            "model": provider_model,
            "live": llm_provider is not None,
            "metadata": metadata,
        },
        "plan": plan,
        "json_plan": json.dumps(plan, ensure_ascii=False, indent=2),
        "agent_trace": plan.get("agent_trace", []),
        "agent_review": plan.get("agent_review", {}),
        "schema_validation": plan.get("schema_validation", {}),
        "mission_svg": render_mission_execution_svg(plan),
    }


def load_demo_benchmark(
    report_path: str | Path | None = DEFAULT_BENCHMARK_REPORT,
    scenario_dir: str | Path = DEFAULT_SCENARIO_DIR,
    benchmark_runner: Callable = run_benchmark_v2,
    scenario_loader: Callable = load_scenarios,
) -> dict[str, Any]:
    if report_path is not None:
        try:
            path = Path(report_path)
            if path.exists():
                report = json.loads(path.read_text(encoding="utf-8-sig"))
                return _normalize_benchmark_report(report, source="saved-report")
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    scenarios = scenario_loader(scenario_dir)
    report = benchmark_runner(scenarios)
    return _normalize_benchmark_report(report, source="offline-fallback")


def load_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_env_quotes(value.strip())
        if key:
            loaded[key] = value
            os.environ.setdefault(key, value)
    return loaded


def _normalize_provider(provider: str | None) -> str:
    provider_name = (provider or "offline").strip().lower()
    if provider_name in {"none", "rule-based"}:
        provider_name = "offline"
    if provider_name not in SUPPORTED_PROVIDERS:
        raise DemoError(400, "unsupported_provider", f"unsupported provider: {provider}")
    return provider_name


def _build_demo_provider(
    *,
    provider_name: str,
    model: str | None,
    base_url: str | None,
    provider_factory: Callable,
) -> Any:
    try:
        return provider_factory(provider_name, model=model, base_url=base_url)
    except LLMProviderError as exc:
        raise DemoError(400, "provider_error", _safe_message(str(exc))) from exc


def _normalize_benchmark_report(report: dict[str, Any], *, source: str) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ValueError("benchmark report must be an object")
    normalized = {
        "status": "ok",
        "source": source,
        "summary": report.get("summary", {}),
        "provider_comparison": report.get("provider_comparison", []),
        "difficulty_summary": report.get("difficulty_summary", []),
        "results": report.get("results", []),
    }
    normalized["json_report"] = json.dumps(normalized, ensure_ascii=False, indent=2)
    return normalized


def _strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _safe_message(message: str) -> str:
    return message.replace("Bearer ", "Bearer [redacted] ")
