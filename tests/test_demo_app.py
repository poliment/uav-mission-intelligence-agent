import re
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


try:
    import fastapi  # noqa: F401
    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False

try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError):
    TestClient = None


class DemoAppTests(unittest.TestCase):
    @unittest.skipIf(FASTAPI_AVAILABLE, "FastAPI is installed")
    def test_create_demo_app_reports_install_hint_when_fastapi_is_missing(self):
        from uav_mission_agent.demo_app import DEMO_INSTALL_HINT, create_demo_app

        with self.assertRaisesRegex(RuntimeError, re.escape(DEMO_INSTALL_HINT)):
            create_demo_app()

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_health_route_reports_ready(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_index_route_returns_json_service_index(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.headers["content-type"])
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "uav-mission-agent-api")
        self.assertIn("/api/swarm/demo-plan", payload["endpoints"])

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_mission_route_returns_offline_payload(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.post(
            "/api/mission",
            json={
                "mission_text": "Use 2 UAVs to inspect area C and avoid no-fly zone D.",
                "provider": "offline",
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["provider"]["name"], "offline")
        self.assertIn("agent_trace", payload)
        self.assertIn("<svg", payload["mission_svg"])

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_mission_route_returns_structured_error_for_empty_mission(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.post("/api/mission", json={"mission_text": " ", "provider": "offline"})

        payload = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "invalid_mission")

    @unittest.skipUnless(TestClient, "FastAPI is not installed")
    def test_benchmark_route_returns_provider_comparison(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/api/benchmark")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("provider_comparison", payload)

    @unittest.skipUnless(TestClient, "FastAPI TestClient dependencies are not installed")
    def test_swarm_demo_plan_route_returns_initial_plan(self):
        from uav_mission_agent.demo_app import create_demo_app

        payload = TestClient(create_demo_app()).get("/api/swarm/demo-plan").json()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["demo"], "swarm")
        self.assertTrue(payload["mission_id"])
        self.assertTrue(payload["mission_text"])
        self.assertEqual(len(payload["swarm_state"]["agents"]), 4)
        self.assertEqual(len(payload["initial_plan"]["role_assignments"]), 4)

    @unittest.skipUnless(TestClient, "FastAPI TestClient dependencies are not installed")
    def test_swarm_demo_events_route_runs_fixed_sequence(self):
        from uav_mission_agent.demo_app import create_demo_app

        payload = TestClient(create_demo_app()).get("/api/swarm/demo-events").json()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["demo"], "swarm")
        self.assertEqual(len(payload["event_responses"]), 3)
        self.assertEqual(len(payload["replanning_memory"]), 3)

    @unittest.skipUnless(TestClient, "FastAPI TestClient dependencies are not installed")
    def test_swarm_demo_dialogue_route_returns_nine_linked_messages(self):
        from uav_mission_agent.demo_app import create_demo_app

        payload = TestClient(create_demo_app()).get("/api/swarm/demo-dialogue").json()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["demo"], "swarm")
        self.assertEqual(len(payload["event_results"]), 3)
        self.assertEqual(len(payload["timeline"]), 9)
        self.assertEqual(len(payload["coordinator_summaries"]), 3)
        self.assertEqual(len(payload["message_memory"]), 9)
        self.assertTrue(all(item["source_message_id"] for item in payload["message_memory"]))

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed")
    def test_mission_route_accepts_json_body_payload(self):
        from uav_mission_agent.demo_app import create_demo_app

        app = create_demo_app()
        route = next(route for route in app.routes if getattr(route, "path", None) == "/api/mission")

        self.assertEqual([param.name for param in route.dependant.query_params], [])
        self.assertEqual([param.name for param in route.dependant.body_params], ["body"])


if __name__ == "__main__":
    unittest.main()
