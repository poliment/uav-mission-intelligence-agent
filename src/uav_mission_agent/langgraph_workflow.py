from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .agent_graph import (
    _knowledge_retriever_agent,
    _mission_planner_agent,
    _mission_reviewer_agent,
    _task_parser_agent,
)
from .knowledge_base import KnowledgeBase
from .llm_provider import LLMProvider
from .schemas import validate_mission_plan


class LangGraphUnavailableError(RuntimeError):
    pass


def run_langgraph_workflow(
    text: str,
    knowledge_base: KnowledgeBase | None = None,
    llm_provider: LLMProvider | None = None,
    graph_api: Any | None = None,
) -> dict[str, Any]:
    app = build_langgraph_app(graph_api=graph_api)
    state = {
        "raw_request": text,
        "knowledge_base": knowledge_base or KnowledgeBase.default(),
        "llm_provider": llm_provider,
        "agent_trace": [],
    }
    final_state = app.invoke(state)
    return _format_langgraph_result(final_state)


def build_langgraph_app(graph_api: Any | None = None):
    api = graph_api or _load_langgraph_api()
    graph = api.StateGraph(dict)
    graph.add_node("task_parser_agent", _as_langgraph_node(_task_parser_agent))
    graph.add_node("knowledge_retriever_agent", _as_langgraph_node(_knowledge_retriever_agent))
    graph.add_node("mission_planner_agent", _as_langgraph_node(_mission_planner_agent))
    graph.add_node("mission_reviewer_agent", _as_langgraph_node(_mission_reviewer_agent))
    graph.add_edge(api.START, "task_parser_agent")
    graph.add_edge("task_parser_agent", "knowledge_retriever_agent")
    graph.add_edge("knowledge_retriever_agent", "mission_planner_agent")
    graph.add_edge("mission_planner_agent", "mission_reviewer_agent")
    graph.add_edge("mission_reviewer_agent", api.END)
    return graph.compile()


def _load_langgraph_api():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise LangGraphUnavailableError(
            "LangGraph backend requires the optional dependency. Install it with: pip install 'uav-mission-intelligence-agent[langgraph]' or pip install langgraph"
        ) from exc
    return SimpleNamespace(StateGraph=StateGraph, START=START, END=END)


def _as_langgraph_node(node_func):
    def _node(state: dict[str, Any]) -> dict[str, Any]:
        node_func(state)
        return state

    return _node


def _format_langgraph_result(state: dict[str, Any]) -> dict[str, Any]:
    plan = state["mission_plan"].to_dict()
    if "llm_metadata" in state:
        plan["llm_metadata"] = state["llm_metadata"]
    plan["schema_validation"] = validate_mission_plan(plan)
    plan["agent_trace"] = [step.to_dict() for step in state["agent_trace"]]
    plan["agent_review"] = state["agent_review"]
    plan["graph_backend"] = "langgraph"
    return plan
