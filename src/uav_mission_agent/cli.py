from __future__ import annotations

import argparse
import json

from .workflow import run_mission_workflow


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a UAV mission intelligence plan.")
    parser.add_argument("mission", help="Natural language UAV mission request.")
    args = parser.parse_args(argv)

    result = run_mission_workflow(args.mission)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

