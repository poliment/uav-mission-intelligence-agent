from __future__ import annotations

from typing import Any

from .knowledge_base import KnowledgeBase
from .llm_provider import LLMProvider, LLMProviderError
from .models import AgentNodeTrace, MissionPlan
from .planner import build_mission_plan
from .schemas import MISSION_PLAN_SCHEMA, validate_mission_plan
from .task_parser import parse_task


AgentState = dict[str, Any]


def run_agent_workflow(
    text: str,
    knowledge_base: KnowledgeBase | None = None,
    llm_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    state: AgentState = {
        "raw_request": text,
        "knowledge_base": knowledge_base or KnowledgeBase.default(),
        "llm_provider": llm_provider,
        "agent_trace": [],
    }
    for node in (
        _task_parser_agent,
        _knowledge_retriever_agent,
        _mission_planner_agent,
        _mission_reviewer_agent,
    ):
        node(state)

    plan = state["mission_plan"].to_dict()
    if "llm_metadata" in state:
        plan["llm_metadata"] = state["llm_metadata"]
    plan["schema_validation"] = validate_mission_plan(plan)
    plan["agent_trace"] = [step.to_dict() for step in state["agent_trace"]]
    plan["agent_review"] = state["agent_review"]
    return plan


def _task_parser_agent(state: AgentState) -> None:
    task = parse_task(state["raw_request"])
    state["task"] = task
    _record(
        state,
        node="task_parser_agent",
        input_keys=["raw_request"],
        output_keys=["task"],
        message="Parsed mission text into UAV task fields.",
    )


def _knowledge_retriever_agent(state: AgentState) -> None:
    snippets = state["knowledge_base"].retrieve(state["raw_request"], limit=3)
    state["retrieved_knowledge"] = snippets
    _record(
        state,
        node="knowledge_retriever_agent",
        input_keys=["raw_request", "knowledge_base"],
        output_keys=["retrieved_knowledge"],
        message=f"Retrieved {len(snippets)} UAV planning knowledge snippets.",
    )


def _mission_planner_agent(state: AgentState) -> None:
    plan = build_mission_plan(state["task"], state["retrieved_knowledge"])
    provider = state.get("llm_provider")
    if provider is not None:
        llm_plan = provider.generate_plan(
            task=state["task"].to_dict(),
            retrieved_knowledge=[snippet.to_dict() for snippet in state["retrieved_knowledge"]],
            baseline_plan=plan.to_dict(),
            output_schema=MISSION_PLAN_SCHEMA,
        )
        plan = _merge_llm_plan(plan, llm_plan)
        state["llm_metadata"] = {
            "provider": provider.provider_name,
            "model": provider.model,
        }
        usage = getattr(provider, "last_usage", None)
        if usage:
            state["llm_metadata"]["usage"] = usage
    state["mission_plan"] = plan
    _record(
        state,
        node="mission_planner_agent",
        input_keys=["task", "retrieved_knowledge", "llm_provider"],
        output_keys=["mission_plan"],
        message="Generated recommendations, risks, and structured mission configuration.",
    )


def _mission_reviewer_agent(state: AgentState) -> None:
    plan = state["mission_plan"].to_dict()
    warnings = _review_plan(plan)
    state["agent_review"] = {
        "ready": not warnings,
        "warning_count": len(warnings),
        "warnings": warnings,
    }
    _record(
        state,
        node="mission_reviewer_agent",
        input_keys=["mission_plan"],
        output_keys=["agent_review"],
        message="Reviewed mission plan completeness and consistency.",
    )


def _review_plan(plan: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    config = plan.get("mission_config", {})
    if not config.get("uav_count"):
        warnings.append("missing_uav_count")
    if not config.get("objectives"):
        warnings.append("missing_objectives")
    if not plan.get("recommendations"):
        warnings.append("missing_recommendations")
    if not plan.get("risks"):
        warnings.append("missing_risks")
    return warnings


def _merge_llm_plan(baseline_plan: MissionPlan, llm_plan: dict[str, Any]) -> MissionPlan:
    if not isinstance(llm_plan, dict):
        raise LLMProviderError("LLM provider output must be a JSON object")
    recommendations = _required_string_list(llm_plan, "recommendations")
    risks = _required_string_list(llm_plan, "risks")
    mission_config = dict(baseline_plan.mission_config)
    if not isinstance(llm_plan.get("mission_config"), dict):
        raise LLMProviderError("LLM provider output field mission_config must be an object")
    mission_config.update(llm_plan["mission_config"])
    merged_plan = MissionPlan(
        task=baseline_plan.task,
        retrieved_knowledge=baseline_plan.retrieved_knowledge,
        recommendations=recommendations,
        risks=risks,
        mission_config=mission_config,
    )
    validation = validate_mission_plan(merged_plan.to_dict())
    if not validation["valid"]:
        details = "; ".join(validation["errors"])
        raise LLMProviderError(f"LLM provider output failed schema validation: {details}")
    return merged_plan


def _required_string_list(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list):
        raise LLMProviderError(f"LLM provider output field {field} must be an array")
    if not all(isinstance(item, str) for item in value):
        raise LLMProviderError(f"LLM provider output field {field} must contain only strings")
    if not value:
        raise LLMProviderError(f"LLM provider output field {field} must not be empty")
    return value


def _record(
    state: AgentState,
    *,
    node: str,
    input_keys: list[str],
    output_keys: list[str],
    message: str,
) -> None:
    state["agent_trace"].append(
        AgentNodeTrace(
            node=node,
            status="ok",
            input_keys=input_keys,
            output_keys=output_keys,
            message=message,
        )
    )
