"""
src/dashboard/app.py

FastAPI transport layer for the live dashboard.

Thin and optional: FastAPI is imported inside ``create_app`` so the dashboard
package can be imported (and its simulation tested) without FastAPI installed.

Endpoints:
  GET  /                — the single-page dashboard (static)
  GET  /api/state       — current ecosystem snapshot (JSON)
  GET  /api/history     — compact time-series for charts (JSON)
  GET  /api/step        — advance one tick and return the new snapshot
  WS   /ws              — push a snapshot every `interval` seconds

Run:
    python -m src.dashboard            # starts uvicorn on :8000
"""

# NOTE: deliberately NOT using ``from __future__ import annotations`` here.
# FastAPI resolves the ``websocket: WebSocket`` parameter via get_type_hints;
# with stringised annotations + a function-local FastAPI import, that name is
# unresolvable and the WebSocket fails to inject. Real annotations avoid this.

import asyncio
from pathlib import Path

from src.dashboard.sim_runner import DashboardSimulation
from src.utils.helpers import get_logger

logger = get_logger("dashboard.app")

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(simulation: DashboardSimulation | None = None, tick_interval: float = 0.5):
    """
    Build and return a FastAPI app bound to a DashboardSimulation.

    FastAPI is imported here (not at module top) so importing this module never
    requires FastAPI to be installed.
    """
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    sim = simulation or DashboardSimulation()
    app = FastAPI(title="Organic Agentic AutoDev — Live Dashboard")
    app.state.simulation = sim
    app.state.tick_interval = tick_interval

    @app.get("/api/state")
    def api_state():
        return JSONResponse(sim.snapshot())

    @app.get("/api/history")
    def api_history():
        return JSONResponse(sim.history())

    @app.get("/api/step")
    def api_step():
        return JSONResponse(sim.step())

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                # sim.step() is synchronous CPU work — run it off the event loop
                # so the websocket stays responsive and the handshake completes.
                snapshot = await asyncio.to_thread(sim.step)
                await websocket.send_json(snapshot)
                await asyncio.sleep(app.state.tick_interval)
        except WebSocketDisconnect:
            logger.debug("Dashboard websocket disconnected")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Dashboard websocket error: %s", exc)

    @app.get("/")
    def index():
        return FileResponse(_STATIC_DIR / "index.html")

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    return app


def run(host: str = "127.0.0.1", port: int = 8000) -> None:  # pragma: no cover
    """Launch the dashboard with uvicorn."""
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)
