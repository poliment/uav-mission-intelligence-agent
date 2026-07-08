from __future__ import annotations

from .agent_graph import run_agent_workflow
from .knowledge_base import KnowledgeBase
from .langgraph_workflow import run_langgraph_workflow
from .llm_provider import LLMProvider


def run_mission_workflow(
    text: str,
    knowledge_base: KnowledgeBase | None = None,
    llm_provider: LLMProvider | None = None,
    graph_backend: str = "rule-based",
    langgraph_runner=None,
) -> dict:
    if graph_backend == "rule-based":
        result = run_agent_workflow(text, knowledge_base=knowledge_base, llm_provider=llm_provider)
    elif graph_backend == "langgraph":
        runner = langgraph_runner or run_langgraph_workflow
        result = runner(text, knowledge_base=knowledge_base, llm_provider=llm_provider)
    else:
        raise ValueError(f"unsupported graph backend: {graph_backend}")
    result.pop("agent_trace", None)
    result.pop("agent_review", None)
    return result
