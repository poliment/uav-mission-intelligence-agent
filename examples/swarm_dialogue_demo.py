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
    session.run_remaining_events()
    data = session.to_dict()
    return {
        "demo_dialogue": {
            "mission_id": data["mission_id"],
            "mission_text": data["mission_text"],
            "initial_plan": data["initial_plan"],
            "event_results": data["event_results"],
            "timeline": data["timeline"],
            "coordinator_summaries": data["coordinator_summaries"],
            "memory_updates": data["message_memory"],
            "swarm_state": data["swarm_state"],
        }
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
