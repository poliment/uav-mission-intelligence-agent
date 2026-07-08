from __future__ import annotations

import re

from .models import KnowledgeSnippet


class KnowledgeBase:
    def __init__(self, snippets: list[KnowledgeSnippet]):
        self._snippets = snippets

    @classmethod
    def default(cls) -> "KnowledgeBase":
        return cls(
            [
                KnowledgeSnippet(
                    topic="coverage_search",
                    content="多无人机搜索任务通常先进行区域分解，再按照覆盖率、航程约束和目标优先级分配航迹。",
                    tags=["多无人机", "搜索", "覆盖", "区域", "area_search"],
                ),
                KnowledgeSnippet(
                    topic="low_bandwidth_coordination",
                    content="弱通信条件下应减少全局同步依赖，优先采用局部感知、事件触发通信和分布式协同策略。",
                    tags=["弱通信", "通信", "低通量", "协同", "distributed"],
                ),
                KnowledgeSnippet(
                    topic="no_fly_zone_avoidance",
                    content="存在禁飞区时，任务配置应显式保留避让区域，并在航迹规划阶段加入硬约束或高惩罚代价。",
                    tags=["禁飞区", "避开", "约束", "航迹规划", "avoid"],
                ),
                KnowledgeSnippet(
                    topic="risk_management",
                    content="无人机任务风险主要来自通信中断、覆盖不足、机间冲突、目标丢失和能量约束。",
                    tags=["风险", "通信", "覆盖不足", "冲突", "能量"],
                ),
            ]
        )

    def retrieve(self, query: str, limit: int = 3) -> list[KnowledgeSnippet]:
        scored = [(self._score(query, snippet), index, snippet) for index, snippet in enumerate(self._snippets)]
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        relevant = [snippet for score, _, snippet in ranked if score > 0]
        if not relevant:
            relevant = [snippet for _, _, snippet in ranked]
        return relevant[:limit]

    @staticmethod
    def _score(query: str, snippet: KnowledgeSnippet) -> int:
        terms = [term for term in re.split(r"[\s,，。；;]+", query) if term]
        score = 0
        for tag in snippet.tags:
            if tag in query:
                score += 3
        for term in terms:
            if term in snippet.content or term in snippet.topic:
                score += 1
        return score

