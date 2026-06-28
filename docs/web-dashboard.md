# Web Dashboard

A live, browser-based view of the running ecosystem: agents differentiating,
organs forming, knowledge growing, and SLOs breaching/recovering in real time.

## Status

✅ Implemented on `feature/web-dashboard`. 12 new tests (7 always-on simulation
tests + 5 FastAPI route/websocket tests); full suite 229 passing. Validated
live (REST + WebSocket + static serving).

## Module map (`organic_agentic_autodev/dashboard/`)

| File | Role | Dependency |
|------|------|-----------|
| `sim_runner.py` | `DashboardSimulation` — observable ecosystem + state shaping | none (stdlib + organic_agentic_autodev) |
| `app.py` | `create_app()` / `run()` — FastAPI transport | FastAPI (optional) |
| `__init__.py` | lazy proxies so the package imports without FastAPI | none |
| `__main__.py` | `python -m organic_agentic_autodev.dashboard` entry point | uvicorn |
| `static/` | `index.html`, `style.css`, `app.js` — no build step | Chart.js via CDN |

## Architecture

The simulation core is **dependency-free** and fully unit-tested offline.
FastAPI is a thin transport layer imported lazily, so:

- `from organic_agentic_autodev.dashboard import DashboardSimulation` works with no web deps.
- `create_app()` imports FastAPI only when called.
- CI stays green without FastAPI (route tests use `pytest.importorskip`).

```
DashboardSimulation (Mouseion + Environment + Network + Body + SLITracker)
        │  .step()  → advance one tick
        │  .snapshot() → JSON state    .history() → chart series
        ▼
   create_app(sim)  ── REST: /api/state /api/history /api/step
        │            ── WS:   /ws  (pushes a snapshot every tick_interval)
        ▼
   static/  index.html + app.js (vanilla JS + Chart.js, WebSocket client)
```

## Endpoints

| Route | Returns |
|-------|---------|
| `GET /` | the single-page dashboard |
| `GET /api/state` | current ecosystem snapshot (JSON) |
| `GET /api/history` | knowledge + compliance time-series |
| `GET /api/step` | advance one tick, return new snapshot |
| `WS /ws` | streams a snapshot every `tick_interval` seconds |
| `GET /static/*` | dashboard assets |

The client uses the WebSocket for live updates and **falls back to polling
`/api/step`** if the socket drops — graceful degradation.

## Snapshot shape

```json
{
  "tick": 42,
  "agents": {"alive": 24, "differentiated": 11, "roles": {"oncologist": 3, ...}},
  "network": {"nodes": 24, "edges": 30, "avg_conductance": 0.21, "signals_delivered": 88},
  "knowledge": {"records": 58, "energy_remaining": 1840.0},
  "organs": [...], "body": {"fully_functional": true, "organs": 3, "visions": 4},
  "sla": {"compliant": true, "compliance_rate": 1.0, "meeting": 6, "breached": 0, "slos": [...]},
  "events": [{"kind": "niche_filled", "source": "sc_..."}, ...]
}
```

## Running

```bash
pip install -e ".[dashboard]"
python -m organic_agentic_autodev.dashboard            # http://127.0.0.1:8000
```

Panels: live metric cards (agents, organs, records, energy), knowledge-growth
and SLA-compliance charts, role distribution, SLO status, and a recent-events
feed. A pause button freezes the view.

## Implementation note

`app.py` deliberately does **not** use `from __future__ import annotations`.
Under stringised annotations, FastAPI's `get_type_hints` cannot resolve the
function-locally-imported `WebSocket` parameter type, so the WebSocket fails to
inject and the handshake silently closes. Real annotations avoid this.
