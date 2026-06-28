"""
src/distributed — multi-process / distributed ecosystem.

Run multiple ecosystems concurrently under asyncio, sharing one Mouseion
substrate and coordinating Body visions through a swappable message bridge
(in-process by default, Redis for true multi-machine deployment).

Public API:
  AsyncEcosystem        — one asyncio-driven ecosystem node
  EcosystemCoordinator  — orchestrates + monitors a colony
  MessageBridge / InProcessBridge / RedisBridge — inter-body transport
  CrossBodyMessage      — the message envelope
  build_colony / run_colony — convenience builders
"""

from __future__ import annotations

from src.distributed.async_environment import AsyncEcosystem
from src.distributed.bridge import (
    CrossBodyMessage,
    InProcessBridge,
    MessageBridge,
    RedisBridge,
)
from src.distributed.coordinator import EcosystemCoordinator
from src.distributed.runner import build_colony, run_colony

__all__ = [
    "AsyncEcosystem",
    "EcosystemCoordinator",
    "MessageBridge",
    "InProcessBridge",
    "RedisBridge",
    "CrossBodyMessage",
    "build_colony",
    "run_colony",
]
