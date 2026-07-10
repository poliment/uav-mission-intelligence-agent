from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


from uav_mission_agent.swarm_coordinator import SwarmCoordinator
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
        mission_id="demo-mountain-a",
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
                battery_level=84.0,
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
    mission_plan = coordinator.plan_mission(
        MISSION_TEXT,
        mission_state,
        timestamp="2026-07-10T09:00:00Z",
    ).to_dict()
    low_battery_event = SwarmEvent(
        event_id="demo-event-low-battery",
        event_type="battery_warning",
        message="UAV-2 battery dropped below the safe reserve threshold.",
        timestamp="2026-07-10T09:10:00Z",
        uav_id="UAV-2",
        severity="warning",
        metadata={"battery_level": 20.0},
    )
    event_response = coordinator.replan_for_event(
        low_battery_event,
        mission_state,
    ).to_dict()
    return {
        "demo_plan": mission_plan,
        "demo_event_response": event_response,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
