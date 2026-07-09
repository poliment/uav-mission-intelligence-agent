from __future__ import annotations

from typing import Any

from .demo_service import DemoError, build_demo_html, build_mission_demo_payload, load_demo_benchmark


DEMO_INSTALL_HINT = "FastAPI demo requires optional dependencies: pip install 'uav-mission-intelligence-agent[demo]'"


def create_demo_app() -> Any:
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(DEMO_INSTALL_HINT) from exc

    app = FastAPI(title="UAV Mission Intelligence Demo")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": "uav-mission-agent-demo"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return build_demo_html()

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

    return app
