from __future__ import annotations

from typing import Any

from .demo_service import DemoError, build_mission_demo_payload, load_demo_benchmark
from .swarm_demo import (
    build_swarm_dialogue_demo_payload,
    build_swarm_events_demo_payload,
    build_swarm_plan_demo_payload,
)


DEMO_INSTALL_HINT = (
    "FastAPI service requires optional dependencies: "
    "pip install 'uav-mission-intelligence-agent[demo]'"
)


def create_demo_app() -> Any:
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(DEMO_INSTALL_HINT) from exc

    app = FastAPI(title="UAV Mission Intelligence API")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "uav-mission-agent-api"}

    @app.get("/")
    def index() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "uav-mission-agent-api",
            "ui_command": "uav-mission-agent-demo",
            "endpoints": {
                "/api/health": "service health",
                "/api/mission": "single-mission planning",
                "/api/benchmark": "offline benchmark report",
                "/api/swarm/demo-plan": "deterministic initial swarm plan",
                "/api/swarm/demo-events": "fixed event response sequence",
                "/api/swarm/demo-dialogue": "multi-agent dialogue timeline",
            },
        }

    @app.get("/api/benchmark")
    def benchmark() -> dict[str, Any]:
        return load_demo_benchmark()

    @app.post("/api/mission")
    async def mission(body: dict[str, Any]):
        try:
            return build_mission_demo_payload(
                mission_text=str(body.get("mission_text", "")),
                provider=str(body.get("provider", "offline")),
                model=body.get("model"),
                base_url=body.get("base_url"),
            )
        except DemoError as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"status": "error", "error": exc.to_dict()},
            )

    @app.get("/api/swarm/demo-plan")
    def swarm_demo_plan() -> dict[str, Any]:
        return build_swarm_plan_demo_payload()

    @app.get("/api/swarm/demo-events")
    def swarm_demo_events() -> dict[str, Any]:
        return build_swarm_events_demo_payload()

    @app.get("/api/swarm/demo-dialogue")
    def swarm_demo_dialogue() -> dict[str, Any]:
        return build_swarm_dialogue_demo_payload()

    return app
