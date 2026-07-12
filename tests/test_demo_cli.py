import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DemoCliTests(unittest.TestCase):
    def test_parser_defaults_to_localhost_and_port_8000(self):
        from uav_mission_agent.demo_cli import build_parser

        args = build_parser().parse_args([])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8000)
        self.assertIsNone(args.env_file)
        self.assertFalse(args.no_browser)

    def test_main_loads_env_file_and_calls_server_runner(self):
        from uav_mission_agent.demo_cli import main

        calls = []

        def fake_runner(host, port, no_browser):
            calls.append({"host": host, "port": port, "no_browser": no_browser})

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "deepseek.env"
            env_path.write_text("DEEPSEEK_API_KEY=demo-key\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                main(
                    [
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8100",
                        "--env-file",
                        str(env_path),
                        "--no-browser",
                    ],
                    server_runner=fake_runner,
                )

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "demo-key")

        self.assertEqual(calls, [{"host": "0.0.0.0", "port": 8100, "no_browser": True}])

    def test_api_cli_loads_env_file_and_calls_uvicorn_runner(self):
        from uav_mission_agent.api_cli import main

        calls = []

        def fake_runner(host, port):
            calls.append({"host": host, "port": port})

        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "api.env"
            env_path.write_text("OPENAI_API_KEY=api-key\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                main(
                    ["--host", "0.0.0.0", "--port", "8200", "--env-file", str(env_path)],
                    server_runner=fake_runner,
                )
                self.assertEqual(os.environ["OPENAI_API_KEY"], "api-key")

        self.assertEqual(calls, [{"host": "0.0.0.0", "port": 8200}])

    def test_pyproject_declares_demo_extra_and_script(self):
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("demo = [", pyproject)
        self.assertIn('"fastapi>=0.100"', pyproject)
        self.assertIn('"uvicorn>=0.23"', pyproject)
        self.assertIn('"streamlit>=1.32,<2"', pyproject)
        self.assertIn('"plotly>=5.22,<6"', pyproject)
        self.assertIn("test = [", pyproject)
        self.assertIn('"httpx2>=2,<3"', pyproject)
        self.assertIn('uav-mission-agent-demo = "uav_mission_agent.demo_cli:main"', pyproject)
        self.assertIn('uav-mission-agent-api = "uav_mission_agent.api_cli:main"', pyproject)


if __name__ == "__main__":
    unittest.main()
