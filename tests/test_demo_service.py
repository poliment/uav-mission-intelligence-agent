import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.demo_service import (
    DemoError,
    build_demo_html,
    build_mission_demo_payload,
    load_demo_benchmark,
    load_env_file,
)
from uav_mission_agent.llm_provider import LLMProviderError


class DemoServiceTests(unittest.TestCase):
    def test_offline_mission_payload_contains_trace_json_and_svg(self):
        payload = build_mission_demo_payload(
            "Use 3 UAVs to search area A, avoid no-fly zone B, and maintain weak communication coordination."
        )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["provider"]["name"], "offline")
        self.assertFalse(payload["provider"]["live"])
        self.assertEqual(payload["plan"]["agent_trace"][0]["node"], "task_parser_agent")
        self.assertIn("mission_planner_agent", [step["node"] for step in payload["agent_trace"]])
        self.assertTrue(payload["schema_validation"]["valid"])
        self.assertIn('"mission_config"', payload["json_plan"])
        self.assertIn("<svg", payload["mission_svg"])
        self.assertIn("Mission Execution Visualization", payload["mission_svg"])

    def test_empty_mission_text_fails_with_validation_error(self):
        with self.assertRaises(DemoError) as raised:
            build_mission_demo_payload("  ")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.code, "invalid_mission")
        self.assertIn("mission text is required", raised.exception.message)

    def test_unsupported_provider_fails_with_validation_error(self):
        with self.assertRaises(DemoError) as raised:
            build_mission_demo_payload("inspect area A", provider="unknown")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.code, "unsupported_provider")
        self.assertIn("unsupported provider", raised.exception.message)

    def test_provider_factory_error_is_wrapped_without_secret_values(self):
        def failing_factory(*args, **kwargs):
            raise LLMProviderError("missing API key: set DEEPSEEK_API_KEY or pass api_key")

        with self.assertRaises(DemoError) as raised:
            build_mission_demo_payload(
                "inspect area A",
                provider="deepseek",
                provider_factory=failing_factory,
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.code, "provider_error")
        self.assertIn("DEEPSEEK_API_KEY", raised.exception.message)

    def test_load_demo_benchmark_prefers_saved_report(self):
        report = {
            "summary": {"benchmark_version": "2.0", "total_scenarios": 31},
            "provider_comparison": [{"provider_label": "deepseek:deepseek-v4-flash", "average_score": 0.935}],
            "difficulty_summary": [],
            "results": [{"scenario_id": "s001", "score": 0.9}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            payload = load_demo_benchmark(report_path=report_path)

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["source"], "saved-report")
        self.assertEqual(payload["summary"]["total_scenarios"], 31)
        self.assertEqual(payload["provider_comparison"][0]["provider_label"], "deepseek:deepseek-v4-flash")
        self.assertIn('"provider_comparison"', payload["json_report"])

    def test_load_demo_benchmark_falls_back_when_report_is_invalid(self):
        fallback_report = {
            "summary": {"benchmark_version": "2.0", "total_scenarios": 1},
            "provider_comparison": [{"provider_label": "offline", "average_score": 0.88}],
            "difficulty_summary": [],
            "results": [{"scenario_id": "fixture", "score": 0.88}],
        }

        def fake_loader(path):
            return ["scenario"]

        def fake_runner(scenarios):
            self.assertEqual(scenarios, ["scenario"])
            return fallback_report

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "broken.json"
            report_path.write_text("{", encoding="utf-8")
            payload = load_demo_benchmark(
                report_path=report_path,
                scenario_dir=Path(tmpdir),
                benchmark_runner=fake_runner,
                scenario_loader=fake_loader,
            )

        self.assertEqual(payload["source"], "offline-fallback")
        self.assertEqual(payload["summary"]["total_scenarios"], 1)
        self.assertEqual(payload["provider_comparison"][0]["provider_label"], "offline")

    def test_load_env_file_sets_values_without_overwriting_existing_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "demo.env"
            env_path.write_text(
                "DEEPSEEK_API_KEY=file-key\n"
                "OPENAI_MODEL='demo-model'\n"
                "# comment line\n"
                "EMPTY_VALUE=\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "existing-key"}, clear=True):
                loaded = load_env_file(env_path)

                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "existing-key")
                self.assertEqual(os.environ["OPENAI_MODEL"], "demo-model")
                self.assertEqual(loaded["OPENAI_MODEL"], "demo-model")
                self.assertEqual(loaded["EMPTY_VALUE"], "")

    def test_demo_html_contains_core_interactive_regions(self):
        html = build_demo_html()

        self.assertIn('id="mission-form"', html)
        self.assertIn('id="mission-text"', html)
        self.assertIn('id="provider-select"', html)
        self.assertIn('id="agent-trace"', html)
        self.assertIn('id="json-output"', html)
        self.assertIn('id="benchmark-table"', html)
        self.assertIn('id="mission-map"', html)
        self.assertIn("/api/mission", html)
        self.assertIn("/api/benchmark", html)


if __name__ == "__main__":
    unittest.main()
