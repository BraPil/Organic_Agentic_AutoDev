# Distributed Ecosystem

Runs multiple ecosystems concurrently under asyncio. They share one Mouseion
knowledge substrate (the commons spans nodes) and coordinate Body visions over a
swappable message bridge, while each evolves its own population, network, and
Body independently.

## Status

✅ Implemented on `feature/distributed-ecosystem`. 12 new tests; full suite 241
passing.

## Module map (`organic_agentic_autodev/distributed/`)

| File | Role | Shell/Flesh |
|------|------|-------------|
| `bridge.py` | `MessageBridge` + `InProcessBridge` (default) + `RedisBridge` (optional) | Shell + Flesh |
| `async_environment.py` | `AsyncEcosystem` — one asyncio-driven node | Flesh |
| `coordinator.py` | `EcosystemCoordinator` — orchestrate + monitor a colony | Flesh |
| `runner.py` | `build_colony()` / `run_colony()` convenience builders | — |

## Architecture

```
                 ┌──────────────── shared Mouseion substrate ────────────────┐
                 │   (one knowledge corpus, read/written by every node)       │
                 └────────────────────────────────────────────────────────────┘
                          ▲              ▲              ▲
        ┌─────────────────┴──┐ ┌─────────┴────────┐ ┌──┴─────────────────┐
        │ AsyncEcosystem A   │ │ AsyncEcosystem B │ │ AsyncEcosystem C   │
        │  env+network+body  │ │  env+network+body│ │  env+network+body  │
        └─────────┬──────────┘ └────────┬─────────┘ └─────────┬──────────┘
                  └──────────── MessageBridge (vision_sync) ───┘
                       InProcessBridge  |  RedisBridge (multi-machine)
```

- **asyncio-first**: each node runs as a coroutine; `step_once()` yields with
  `await asyncio.sleep(0)` so nodes interleave cooperatively. The coordinator
  runs them with `asyncio.gather(..., return_exceptions=True)`.
- **Shared substrate**: all nodes are constructed with the *same* `Mouseion`
  instance, so knowledge written by one is immediately visible to all. (For true
  multi-process, point each at a `SQLiteBackend` Mouseion on the same DB.)
- **Inter-body bridge**: when a Body produces a new vision, its node publishes a
  `CrossBodyMessage` on the `vision_sync` topic; every *other* node receives it
  and re-broadcasts a SYNC signal into its local slime mold network. A node
  ignores its own echo.

## Message bridge

| Implementation | Use |
|----------------|-----|
| `InProcessBridge` (default) | single-process colony; zero dependencies |
| `RedisBridge` (optional) | true multi-process / multi-machine via Redis Pub/Sub (`pip install -e ".[distributed]"`) |

Both implement the same `MessageBridge` async pub/sub interface, so swapping is a
one-line change. The bridge tolerates a failing subscriber (logs and continues).

## Graceful degradation

- A node that raises mid-run is recorded in the coordinator's failure map; the
  surviving nodes still complete (`return_exceptions=True`).
- A node can `disconnect()` from the bridge (simulating going offline) — it
  stops receiving cross-body messages — then `reconnect()` to resume. No
  messages are buffered for an offline node; it re-syncs on the next vision.

## Usage

```python
import asyncio
from organic_agentic_autodev.distributed import build_colony

async def main():
    coordinator = build_colony(n_nodes=4, agents_per_node=8, seed=42)
    health = await coordinator.run(ticks=40)
    print(health["node_status"])
    await coordinator.close()

asyncio.run(main())
```

Or the one-call form: `await run_colony(n_nodes=4, ticks=40)`.

## Demo

```bash
python examples/distributed_demo.py
```

Shows 4 ecosystems running concurrently, all reading one shared substrate, and a
Body vision propagating from one node to every peer over the bridge.

## Multi-machine note

For separate processes/machines:
1. Give each process a `Mouseion(backend=SQLiteBackend("shared.db"))` pointing at
   shared storage (WAL mode supports concurrent readers).
2. Use `RedisBridge("redis://host:6379/0")` so vision sync crosses process
   boundaries.

Both are flesh swaps — the `AsyncEcosystem` and `EcosystemCoordinator` code is
unchanged.
