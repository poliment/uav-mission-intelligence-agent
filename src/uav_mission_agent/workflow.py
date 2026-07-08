from __future__ import annotations

from .knowledge_base import KnowledgeBase
from .planner import build_mission_plan
from .task_parser import parse_task


def run_mission_workflow(text: str, knowledge_base: KnowledgeBase | None = None) -> dict:
    task = parse_task(text)
    knowledge = knowledge_base or KnowledgeBase.default()
    snippets = knowledge.retrieve(text, limit=3)
    plan = build_mission_plan(task, snippets)
    return plan.to_dict()

