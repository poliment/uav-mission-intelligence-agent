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
    def test_index_route_returns_demo_html(self):
        from uav_mission_agent.demo_app import create_demo_app

        client = TestClient(create_demo_app())
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("UAV Mission Intelligence Demo", response.text)
        self.assertIn('id="mission-form"', response.text)

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

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed")
    def test_mission_route_accepts_json_body_payload(self):
        from uav_mission_agent.demo_app import create_demo_app

        app = create_demo_app()
        route = next(route for route in app.routes if getattr(route, "path", None) == "/api/mission")

        self.assertEqual([param.name for param in route.dependant.query_params], [])
        self.assertEqual([param.name for param in route.dependant.body_params], ["body"])


if __name__ == "__main__":
    unittest.main()
