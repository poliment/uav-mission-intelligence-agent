from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
APP_PATH = PROJECT_ROOT / "src" / "uav_mission_agent" / "streamlit_app.py"


try:
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


def _widget(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


class FailingProvider:
    provider_name = "deepseek"
    model = "failing-model"

    def generate_plan(self, **kwargs):
        raise RuntimeError("simulated provider outage")


@unittest.skipUnless(AppTest, "Streamlit is not installed")
class StreamlitAppTests(unittest.TestCase):
    def run_app(self):
        app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
        self.assertEqual([item.value for item in app.exception], [])
        return app

    def test_first_run_initializes_offline_console_and_five_views(self):
        app = self.run_app()

        session = app.session_state["swarm_demo_session"]
        self.assertEqual(session.initial_plan.decision_source, "offline_rules")
        self.assertEqual(session.event_results, [])
        self.assertEqual(_widget(app.selectbox, "Provider").value, "offline")
        view = _widget(app.radio, "View")
        self.assertEqual(view.value, "Swarm Plan")
        self.assertEqual(
            list(view.options),
            [
                "Swarm Plan",
                "Event Response",
                "Agent Dialogue",
                "Mission Intelligence",
                "Evaluation",
            ],
        )
        self.assertTrue(any(metric.label == "Active UAVs" for metric in app.metric))
        self.assertTrue(any("初始角色" in item.value for item in app.caption))

    def test_event_view_processes_one_event_in_order(self):
        app = self.run_app()
        app = _widget(app.radio, "View").set_value("Event Response").run()
        app = _widget(app.button, "Process next event").click().run()

        session = app.session_state["swarm_demo_session"]
        self.assertEqual(len(session.event_results), 1)
        self.assertEqual(session.event_results[0].trigger_event.event_type, "target_detected")
        self.assertEqual(session.next_event_type, "battery_warning")
        self.assertTrue(any("battery_warning" in item.value for item in app.caption))

    def test_run_remaining_populates_dialogue_timeline_and_memory_links(self):
        app = self.run_app()
        app = _widget(app.radio, "View").set_value("Event Response").run()
        app = _widget(app.button, "Run remaining").click().run()
        app = _widget(app.radio, "View").set_value("Agent Dialogue").run()

        session = app.session_state["swarm_demo_session"]
        self.assertEqual(len(session.event_results), 3)
        self.assertEqual(
            sum(len(result.messages) for result in session.event_results),
            9,
        )
        self.assertTrue(any("9 structured messages" in item.value for item in app.caption))
        self.assertTrue(any("Memory links" in item.value for item in app.subheader))

    def test_provider_error_is_shown_without_replacing_current_session(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
            app = self.run_app()
            original_session = app.session_state["swarm_demo_session"]
            app = _widget(app.selectbox, "Provider").set_value("deepseek").run()
            app = _widget(app.button, "Initialize Mission").click().run()

        self.assertTrue(app.error)
        self.assertIn("DEEPSEEK_API_KEY", app.error[0].value)
        self.assertIs(app.session_state["swarm_demo_session"], original_session)

    def test_provider_runtime_fallback_is_labeled_as_offline(self):
        with patch(
            "uav_mission_agent.llm_provider.build_llm_provider",
            return_value=FailingProvider(),
        ):
            app = self.run_app()
            app = _widget(app.selectbox, "Provider").set_value("deepseek").run()
            app = _widget(app.button, "Initialize Mission").click().run()

        session = app.session_state["swarm_demo_session"]
        self.assertEqual(session.initial_plan.decision_source, "offline_rules")
        self.assertEqual(
            session.initial_plan.provider_advisory["status"],
            "offline_fallback",
        )
        self.assertTrue(app.warning)
        self.assertIn("offline fallback", app.warning[0].value.lower())
        provider_metric = next(metric for metric in app.metric if metric.label == "Provider")
        self.assertEqual(provider_metric.value, "offline fallback")

    def test_reset_restores_default_offline_unprocessed_session(self):
        app = self.run_app()
        app = _widget(app.radio, "View").set_value("Event Response").run()
        app = _widget(app.button, "Process next event").click().run()
        self.assertEqual(len(app.session_state["swarm_demo_session"].event_results), 1)

        app = _widget(app.button, "Reset").click().run()

        session = app.session_state["swarm_demo_session"]
        self.assertEqual(session.event_results, [])
        self.assertEqual(session.next_event_type, "target_detected")
        self.assertEqual(_widget(app.selectbox, "Provider").value, "offline")

    def test_swarm_plan_remains_the_initial_snapshot_after_events(self):
        app = self.run_app()
        app = _widget(app.radio, "View").set_value("Event Response").run()
        app = _widget(app.button, "Run remaining").click().run()
        app = _widget(app.radio, "View").set_value("Swarm Plan").run()

        session = app.session_state["swarm_demo_session"]
        expected_roles = {
            assignment.uav_id: assignment.role
            for assignment in session.initial_plan.role_assignments
        }
        role_rows = app.dataframe[0].value.to_dict(orient="records")
        self.assertEqual(
            {row["UAV"]: row["role"] for row in role_rows},
            expected_roles,
        )

        plot_spec = json.loads(app.get("plotly_chart")[0].proto.figure.spec)
        uav_trace = next(trace for trace in plot_spec["data"] if trace["name"] == "UAVs")
        self.assertEqual(list(uav_trace["x"]), [0, 1, 0, 1])
        self.assertEqual(list(uav_trace["y"]), [0, 0, 1, 1])

    def test_mission_intelligence_and_evaluation_views_render(self):
        app = self.run_app()
        app = _widget(app.radio, "View").set_value("Mission Intelligence").run()

        self.assertEqual([item.value for item in app.exception], [])
        self.assertTrue(any(item.value == "Agent trace" for item in app.subheader))
        self.assertTrue(any(item.value == "Validation" for item in app.subheader))

        app = _widget(app.radio, "View").set_value("Evaluation").run()

        self.assertEqual([item.value for item in app.exception], [])
        scenario_metric = next(metric for metric in app.metric if metric.label == "Scenarios")
        self.assertEqual(scenario_metric.value, "31")
        self.assertTrue(any(item.value == "Provider comparison" for item in app.subheader))

    def test_source_uses_no_unsafe_html_or_api_key_widget(self):
        source = APP_PATH.read_text(encoding="utf-8")

        self.assertNotIn("unsafe_allow_html", source)
        self.assertNotIn("API key", source)


if __name__ == "__main__":
    unittest.main()
