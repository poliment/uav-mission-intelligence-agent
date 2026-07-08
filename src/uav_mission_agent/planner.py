from __future__ import annotations

from .models import KnowledgeSnippet, MissionPlan, TaskSpec


def build_mission_plan(task: TaskSpec, snippets: list[KnowledgeSnippet]) -> MissionPlan:
    recommendations = _build_recommendations(task)
    risks = _build_risks(task)
    mission_config = {
        "version": "0.1",
        "uav_count": task.drone_count,
        "search_areas": task.search_areas or ["unspecified_area"],
        "avoid_zones": task.avoid_zones,
        "objectives": task.objectives,
        "constraints": task.constraints,
        "coordination_mode": _coordination_mode(task),
        "planning_policy": _planning_policy(task),
    }

    return MissionPlan(
        task=task,
        retrieved_knowledge=snippets,
        recommendations=recommendations,
        risks=risks,
        mission_config=mission_config,
    )


def _build_recommendations(task: TaskSpec) -> list[str]:
    recommendations: list[str] = []
    if "area_search" in task.objectives:
        area_text = "、".join(task.search_areas) if task.search_areas else "待搜索区域"
        recommendations.append(f"将{area_text}划分为若干子区域，并按无人机数量进行覆盖搜索任务分配。")
    if "suspicious_target_search" in task.objectives:
        recommendations.append("对可疑目标点设置更高搜索优先级，并在目标附近保留重访或盘旋观察策略。")
    if "avoid_no_fly_zone" in task.constraints:
        zone_text = "、".join(task.avoid_zones) if task.avoid_zones else "禁飞区"
        recommendations.append(f"将{zone_text}作为硬约束写入任务配置，规划阶段禁止航迹穿越。")
    if "low_bandwidth_coordination" in task.constraints:
        recommendations.append("采用分布式协同策略，降低全局同步频率，仅在关键事件或区域交接时通信。")
    if "replanning" in task.objectives:
        recommendations.append("检测到动态约束变化时触发局部重规划，并重新检查航程、避障和覆盖完整性。")
    if "target_tracking" in task.objectives:
        recommendations.append("采用多机接力跟踪策略，保持目标持续观测并降低单机遮挡或目标丢失风险。")
    if not recommendations:
        recommendations.append("先进行任务目标、区域边界和约束条件确认，再生成无人机任务配置。")
    return recommendations


def _build_risks(task: TaskSpec) -> list[str]:
    risks: list[str] = []
    if "low_bandwidth_coordination" in task.constraints:
        risks.append("弱通信可能导致任务状态不同步，需要设计局部决策和失联降级策略。")
    if task.avoid_zones:
        risks.append("禁飞区约束会压缩可行航迹空间，需检查绕飞后航程和覆盖率是否满足要求。")
    if task.drone_count > 1:
        risks.append("多机协同需要关注机间冲突、任务重复覆盖和区域交接失败。")
    if "target_tracking" in task.objectives:
        risks.append("目标跟踪任务需要关注目标丢失、遮挡和多机重复跟踪。")
    if not risks:
        risks.append("任务约束较少，但仍需补充区域边界、飞行高度和续航限制。")
    return risks


def _coordination_mode(task: TaskSpec) -> str:
    if "low_bandwidth_coordination" in task.constraints:
        return "distributed_low_bandwidth"
    if task.drone_count > 1:
        return "distributed_cooperative"
    return "single_uav"


def _planning_policy(task: TaskSpec) -> str:
    if "target_tracking" in task.objectives:
        return "target_tracking_with_distributed_coordination"
    if "replanning" in task.objectives:
        return "dynamic_replanning_with_constraint_avoidance"
    if "area_search" in task.objectives or "coverage" in task.objectives:
        return "coverage_first_with_constraint_avoidance"
    return "mission_planning_with_constraint_check"
