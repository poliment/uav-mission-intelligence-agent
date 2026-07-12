from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


from uav_mission_agent.swarm_demo import create_swarm_demo_session


def run_demo() -> dict[str, Any]:
    session = create_swarm_demo_session()
    session.process_next_event()
    battery_response = session.process_next_event().coordination_result
    return {
        "demo_plan": session.initial_plan.to_dict(),
        "demo_event_response": battery_response.to_dict(),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
