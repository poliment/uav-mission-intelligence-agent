from __future__ import annotations

import re

from .models import TaskSpec


CHINESE_DIGITS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def parse_task(text: str) -> TaskSpec:
    request = text.strip()
    return TaskSpec(
        raw_request=request,
        drone_count=_extract_drone_count(request),
        search_areas=_extract_regions(request),
        avoid_zones=_extract_avoid_zones(request),
        objectives=_extract_objectives(request),
        constraints=_extract_constraints(request),
    )


def _extract_drone_count(text: str) -> int:
    digit_match = re.search(r"(\d+)\s*架\s*(?:无人机|UAV|uav)?", text)
    if digit_match:
        return int(digit_match.group(1))

    chinese_match = re.search(r"([一二两三四五六七八九十])\s*架\s*(?:无人机)?", text)
    if chinese_match:
        return CHINESE_DIGITS[chinese_match.group(1)]

    english_match = re.search(r"\b(\d+)\s*(?:UAVs?|uavs?|drones?)\b", text)
    if english_match:
        return int(english_match.group(1))

    return 1


def _extract_objectives(text: str) -> list[str]:
    lowered = text.lower()
    objectives: list[str] = []
    if (
        "搜索" in text
        or "搜寻" in text
        or "侦察" in text
        or "巡检" in text
        or "巡查" in text
        or "search" in lowered
        or "scan" in lowered
        or "recon" in lowered
        or "inspect" in lowered
    ):
        objectives.append("area_search")
    if "覆盖" in text or "coverage" in lowered or "cover" in lowered:
        objectives.append("coverage")
    if "可疑目标" in text or "目标点" in text:
        objectives.append("suspicious_target_search")
    if "重新规划" in text or "重规划" in text or "再规划" in text or "replan" in lowered or "reroute" in lowered:
        objectives.append("replanning")
    if "跟踪" in text or "追踪" in text or "track" in lowered:
        objectives.append("target_tracking")
    if not objectives:
        objectives.append("mission_planning")
    return objectives


def _extract_constraints(text: str) -> list[str]:
    lowered = text.lower()
    constraints: list[str] = []
    if "弱通信" in text or "低通量" in text or "通信受限" in text or "weak comm" in lowered or "low bandwidth" in lowered:
        constraints.append("low_bandwidth_coordination")
    if "禁飞区" in text or "避开" in text or "nfz" in lowered or "no-fly" in lowered or "avoid" in lowered:
        constraints.append("avoid_no_fly_zone")
    if "协同" in text or "集群" in text or "多无人机" in text or "swarm" in lowered or "coordinat" in lowered:
        constraints.append("multi_uav_coordination")
    if "避障" in text or "障碍" in text or "obstacle" in lowered or "blocked" in lowered:
        constraints.append("obstacle_avoidance")
    return constraints


def _extract_unique(pattern: str, text: str, flags: int = 0) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for value in re.findall(pattern, text, flags):
        cleaned = value.rstrip("，。,.；;")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            values.append(cleaned)
    return values


def _extract_labeled_regions(label: str, text: str) -> list[str]:
    # Capture compact labels such as 区域A or 禁飞区D without swallowing following prose.
    ascii_values = _extract_unique(rf"({label}[0-9A-Za-z_-]+)", text)
    if ascii_values:
        return ascii_values
    return _extract_unique(rf"({label}[\u4e00-\u9fff])", text)


def _extract_regions(text: str) -> list[str]:
    values = _extract_labeled_regions("区域", text)
    values.extend(_extract_unique(r"\b(area[_-]?[0-9A-Za-z]+)\b", text, flags=re.IGNORECASE))
    return _dedupe(values)


def _extract_avoid_zones(text: str) -> list[str]:
    values = _extract_labeled_regions("禁飞区", text)
    values.extend(_extract_unique(r"\b(NFZ[_-]?[0-9A-Za-z]+)\b", text, flags=re.IGNORECASE))
    values.extend(_extract_unique(r"\b(no[-_ ]fly[-_ ]zone[_-]?[0-9A-Za-z]+)\b", text, flags=re.IGNORECASE))
    return _dedupe(values)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
