from __future__ import annotations

import argparse
import json

from .agent_graph import run_agent_workflow
from .benchmark import run_benchmark
from .dashboard import DEFAULT_MISSION_TEXT, DEFAULT_SCENARIO_DIR, write_dashboard
from .scenario_loader import load_scenarios
from .workflow import run_mission_workflow


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a UAV mission intelligence plan.")
    parser.add_argument("mission", nargs="?", help="Natural language UAV mission request.")
    parser.add_argument("--benchmark", help="Directory containing UAV mission scenario JSON files.")
    parser.add_argument("--dashboard", help="Write a local HTML dashboard to this path.")
    parser.add_argument("--trace", action="store_true", help="Show Agent node trace for a single mission.")
    args = parser.parse_args(argv)

    if args.dashboard:
        mission = args.mission or DEFAULT_MISSION_TEXT
        scenario_dir = args.benchmark or DEFAULT_SCENARIO_DIR
        dashboard_path = write_dashboard(args.dashboard, mission, scenario_dir)
        result = {
            "dashboard": str(dashboard_path),
            "mission": mission,
            "scenario_dir": str(scenario_dir),
        }
    elif args.benchmark:
        result = run_benchmark(load_scenarios(args.benchmark))
    elif args.mission:
        result = run_agent_workflow(args.mission) if args.trace else run_mission_workflow(args.mission)
    else:
        parser.error("provide a mission string, --benchmark SCENARIO_DIR, or --dashboard OUTPUT_HTML")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
