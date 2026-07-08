from __future__ import annotations

import argparse
import json

from .agent_graph import run_agent_workflow
from .benchmark import run_benchmark
from .dashboard import DEFAULT_MISSION_TEXT, DEFAULT_SCENARIO_DIR, write_dashboard
from .llm_provider import LLMProviderError, build_llm_provider
from .schemas import build_schema_output
from .scenario_loader import load_scenarios
from .workflow import run_mission_workflow


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a UAV mission intelligence plan.")
    parser.add_argument("mission", nargs="?", help="Natural language UAV mission request.")
    parser.add_argument("--benchmark", help="Directory containing UAV mission scenario JSON files.")
    parser.add_argument("--dashboard", help="Write a local HTML dashboard to this path.")
    parser.add_argument(
        "--schema-output",
        action="store_true",
        help="Wrap a mission result in the public JSON schema envelope.",
    )
    parser.add_argument(
        "--llm-provider",
        default="none",
        choices=["none", "offline", "openai-compatible", "deepseek"],
        help="Optional LLM provider for mission planning refinement.",
    )
    parser.add_argument("--llm-model", help="Model name for the selected LLM provider.")
    parser.add_argument("--llm-base-url", help="Base URL for an OpenAI-compatible API.")
    parser.add_argument(
        "--llm-api-key-env",
        help="Environment variable that stores the LLM API key. Defaults to OPENAI_API_KEY or DEEPSEEK_API_KEY.",
    )
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
        llm_provider = _build_cli_llm_provider(args, parser)
        result = (
            run_agent_workflow(args.mission, llm_provider=llm_provider)
            if args.trace
            else run_mission_workflow(args.mission, llm_provider=llm_provider)
        )
        if args.schema_output:
            result = build_schema_output(result)
    else:
        parser.error("provide a mission string, --benchmark SCENARIO_DIR, or --dashboard OUTPUT_HTML")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _build_cli_llm_provider(args: argparse.Namespace, parser: argparse.ArgumentParser):
    try:
        return build_llm_provider(
            args.llm_provider,
            api_key_env=args.llm_api_key_env,
            model=args.llm_model,
            base_url=args.llm_base_url,
        )
    except LLMProviderError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
