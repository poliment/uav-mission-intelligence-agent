from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .demo_service import load_env_file


DEMO_INSTALL_HINT = (
    "Streamlit demo requires optional dependencies: "
    "pip install 'uav-mission-intelligence-agent[demo]'"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the UAV Mission Intelligence interactive demo.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for the demo server.")
    parser.add_argument("--port", type=int, default=8000, help="Port for the demo server.")
    parser.add_argument("--env-file", help="Optional KEY=value env file for provider credentials.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start Streamlit without opening a browser window.",
    )
    return parser


def run_server(host: str, port: int, no_browser: bool = False) -> None:
    try:
        from streamlit.web import cli as streamlit_cli
    except ModuleNotFoundError as exc:
        raise RuntimeError(DEMO_INSTALL_HINT) from exc

    app_path = Path(__file__).with_name("streamlit_app.py")
    streamlit_args = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        str(no_browser).lower(),
    ]
    previous_argv = sys.argv
    try:
        sys.argv = streamlit_args
        streamlit_cli.main()
    finally:
        sys.argv = previous_argv


def main(argv: list[str] | None = None, server_runner=run_server) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.env_file:
        load_env_file(args.env_file)
    server_runner(args.host, args.port, args.no_browser)


if __name__ == "__main__":
    main()
