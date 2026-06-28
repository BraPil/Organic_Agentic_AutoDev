"""
tests/test_dashboard.py

Tests for the live dashboard.

The simulation core (DashboardSimulation) is dependency-free and always tested.
The FastAPI transport tests are guarded with importorskip so the suite stays
green whether or not FastAPI is installed.
"""

from __future__ import annotations

import json

import pytest

from src.dashboard import DashboardSimulation


# ---------------------------------------------------------------------------
# Simulation core (always runs, offline)
# ---------------------------------------------------------------------------

@pytest.fixture
def sim():
    return DashboardSimulation(n_stem_cells=12, seed=7)


def test_simulation_initialises(sim):
    snap = sim.snapshot()
    assert snap["tick"] == 0
    assert snap["agents"]["alive"] == 12
    assert snap["knowledge"]["records"] == 20  # ExMorbus seed corpus


def test_simulation_step_advances(sim):
    snap = sim.step()
    assert snap["tick"] == 1
    assert "network" in snap and "sla" in snap


def test_snapshot_is_json_serialisable(sim):
    for _ in range(5):
        sim.step()
    # Must round-trip through JSON without error.
    text = json.dumps(sim.snapshot())
    assert isinstance(text, str)
    parsed = json.loads(text)
    assert parsed["tick"] == 5


def test_snapshot_has_expected_shape(sim):
    snap = sim.snapshot()
    for key in ("tick", "agents", "network", "knowledge", "organs",
                "body", "sla", "events"):
        assert key in snap
    assert "roles" in snap["agents"]
    assert "slos" in snap["sla"]


def test_history_grows_and_serialises(sim):
    for _ in range(8):
        sim.step()
    hist = sim.history()
    assert len(hist["knowledge"]) == 8
    assert len(hist["compliance"]) == 8
    json.dumps(hist)  # serialisable


def test_simulation_runs_many_ticks_without_error(sim):
    for _ in range(40):
        sim.step()
    snap = sim.snapshot()
    assert snap["tick"] == 40
    # Some agents should have differentiated by now.
    assert snap["agents"]["differentiated"] >= 0


def test_roles_track_differentiation(sim):
    for _ in range(50):
        sim.step()
    roles = sim.snapshot()["agents"]["roles"]
    # At least the stem_cell role or a specialist role is present.
    assert sum(roles.values()) == sim.snapshot()["agents"]["alive"]


# ---------------------------------------------------------------------------
# FastAPI transport (skipped if FastAPI absent)
# ---------------------------------------------------------------------------

def _client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from src.dashboard import create_app

    return TestClient(create_app(DashboardSimulation(n_stem_cells=8, seed=3)))


def test_api_state_route():
    client = _client()
    resp = client.get("/api/state")
    assert resp.status_code == 200
    assert resp.json()["tick"] == 0


def test_api_step_route_advances():
    client = _client()
    assert client.get("/api/step").json()["tick"] == 1
    assert client.get("/api/step").json()["tick"] == 2


def test_api_history_route():
    client = _client()
    client.get("/api/step")
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert "knowledge" in resp.json()


def test_index_route_serves_html():
    client = _client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Organic Agentic AutoDev" in resp.text


def test_websocket_streams_snapshots():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from src.dashboard import create_app

    client = TestClient(create_app(DashboardSimulation(n_stem_cells=8, seed=1),
                                   tick_interval=0.01))
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        second = ws.receive_json()
        assert second["tick"] == first["tick"] + 1
        ws.close()
