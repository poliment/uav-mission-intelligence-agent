from __future__ import annotations

from .agent_graph import run_agent_workflow
from .knowledge_base import KnowledgeBase


def run_mission_workflow(text: str, knowledge_base: KnowledgeBase | None = None) -> dict:
    result = run_agent_workflow(text, knowledge_base=knowledge_base)
    result.pop("agent_trace", None)
    result.pop("agent_review", None)
    return result
