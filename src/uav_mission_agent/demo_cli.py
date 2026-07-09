from __future__ import annotations

import argparse

from .demo_service import load_env_file


DEMO_INSTALL_HINT = "FastAPI demo requires optional dependencies: pip install 'uav-mission-intelligence-agent[demo]'"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the UAV Mission Intelligence interactive demo.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the demo server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the demo server.")
    parser.add_argument("--env-file", help="Optional KEY=value env file for provider credentials.")
    return parser


def run_server(host: str, port: int) -> None:
    try:
        import uvicorn
        from .demo_app import create_demo_app
    except ModuleNotFoundError as exc:
        raise RuntimeError(DEMO_INSTALL_HINT) from exc

    uvicorn.run(create_demo_app(), host=host, port=port)


def main(argv: list[str] | None = None, server_runner=run_server) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.env_file:
        load_env_file(args.env_file)
    server_runner(args.host, args.port)


if __name__ == "__main__":
    main()
