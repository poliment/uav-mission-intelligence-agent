from __future__ import annotations

from typing import Any

from .knowledge_base import KnowledgeBase
from .models import AgentNodeTrace
from .planner import build_mission_plan
from .task_parser import parse_task


AgentState = dict[str, Any]


def run_agent_workflow(text: str, knowledge_base: KnowledgeBase | None = None) -> dict[str, Any]:
    state: AgentState = {
        "raw_request": text,
        "knowledge_base": knowledge_base or KnowledgeBase.default(),
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
    state["mission_plan"] = plan
    _record(
        state,
        node="mission_planner_agent",
        input_keys=["task", "retrieved_knowledge"],
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

