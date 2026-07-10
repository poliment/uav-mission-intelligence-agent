from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


from uav_mission_agent.swarm_coordinator import SwarmCoordinator
from uav_mission_agent.swarm_dialogue import SwarmDialogueEngine
from uav_mission_agent.swarm_environment import SwarmGridEnvironment
from uav_mission_agent.swarm_models import (
    GridPosition,
    SwarmEvent,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)


MISSION_TEXT = (
    "使用4架无人机搜索山区A，优先寻找疑似热源目标，其中1架保持通信中继，"
    "低电量无人机不得进入远端区域。"
)


def run_demo() -> dict[str, Any]:
    environment = SwarmGridEnvironment(
        width=20,
        height=20,
        base_position=GridPosition(0, 0),
        communication_center=GridPosition(0, 0),
        communication_range=30.0,
        obstacles=[GridPosition(6, 5), GridPosition(6, 6)],
        no_fly_zones=[GridPosition(8, 8)],
        battery_drain_per_step=1.0,
        low_battery_threshold=25.0,
    )
    mission_state = SwarmMissionState(
        mission_id="demo-dialogue-mountain-a",
        agents=[
            UAVAgentState(
                uav_id="UAV-1",
                role="unassigned",
                position=GridPosition(0, 0),
                battery_level=92.0,
            ),
            UAVAgentState(
                uav_id="UAV-2",
                role="unassigned",
                position=GridPosition(1, 0),
                battery_level=88.0,
            ),
            UAVAgentState(
                uav_id="UAV-3",
                role="unassigned",
                position=GridPosition(0, 1),
                battery_level=96.0,
            ),
            UAVAgentState(
                uav_id="UAV-4",
                role="unassigned",
                position=GridPosition(1, 1),
                battery_level=76.0,
            ),
        ],
        memory=SwarmMemory(),
        base_position=GridPosition(0, 0),
        grid_size={"width": 20, "height": 20},
    )
    coordinator = SwarmCoordinator(environment)
    initial_plan = coordinator.plan_mission(
        MISSION_TEXT,
        mission_state,
        timestamp="2026-07-10T10:00:00Z",
    ).to_dict()
    dialogue = SwarmDialogueEngine(coordinator)

    target_result = dialogue.coordinate_event(
        SwarmEvent(
            event_id="demo-dialogue-target",
            event_type="target_detected",
            message="UAV-1 detected a thermal source.",
            timestamp="2026-07-10T10:05:00Z",
            uav_id="UAV-1",
            target_id="target-thermal-1",
            area_id="山区A-east",
            metadata={
                "target_type": "thermal_source",
                "position": {"x": 12, "y": 8},
                "confidence": 0.91,
            },
        ),
        mission_state,
    ).to_dict()

    battery_result = dialogue.coordinate_event(
        SwarmEvent(
            event_id="demo-dialogue-battery",
            event_type="battery_warning",
            message="UAV-2 battery dropped below the reserve threshold.",
            timestamp="2026-07-10T10:08:00Z",
            uav_id="UAV-2",
            severity="warning",
            metadata={"battery_level": 20.0},
        ),
        mission_state,
    ).to_dict()

    affected = next(agent for agent in mission_state.agents if agent.uav_id == "UAV-1")
    affected.position = GridPosition(18, 18)
    affected.communication_quality = 0.2
    communication_result = dialogue.coordinate_event(
        SwarmEvent(
            event_id="demo-dialogue-communication",
            event_type="communication_degraded",
            message="UAV-1 communication quality dropped below threshold.",
            timestamp="2026-07-10T10:10:00Z",
            uav_id="UAV-1",
            severity="warning",
            metadata={"communication_quality": 0.2},
        ),
        mission_state,
    ).to_dict()

    event_results = [target_result, battery_result, communication_result]
    timeline = [
        message
        for result in event_results
        for message in result["messages"]
    ]
    memory_updates = [
        event
        for result in event_results
        for event in result["memory_updates"]
    ]
    return {
        "demo_dialogue": {
            "mission_id": mission_state.mission_id,
            "mission_text": MISSION_TEXT,
            "initial_plan": initial_plan,
            "event_results": event_results,
            "timeline": timeline,
            "coordinator_summaries": [
                result["coordinator_summary"] for result in event_results
            ],
            "memory_updates": memory_updates,
            "swarm_state": mission_state.to_dict(),
        }
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
