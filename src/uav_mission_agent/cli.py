from __future__ import annotations

import argparse
import json

from .benchmark import run_benchmark
from .scenario_loader import load_scenarios
from .workflow import run_mission_workflow


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a UAV mission intelligence plan.")
    parser.add_argument("mission", nargs="?", help="Natural language UAV mission request.")
    parser.add_argument("--benchmark", help="Directory containing UAV mission scenario JSON files.")
    args = parser.parse_args(argv)

    if args.benchmark:
        result = run_benchmark(load_scenarios(args.benchmark))
    elif args.mission:
        result = run_mission_workflow(args.mission)
    else:
        parser.error("provide a mission string or --benchmark SCENARIO_DIR")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
