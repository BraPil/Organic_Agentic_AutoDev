"""
src/dashboard — live web dashboard for observing emergent behaviour.

The simulation core (DashboardSimulation) is dependency-free and unit-tested
offline. The FastAPI transport (create_app / run) is optional flesh — install
it with ``pip install -e ".[dashboard]"``.
"""

from __future__ import annotations

from src.dashboard.sim_runner import DashboardSimulation

__all__ = ["DashboardSimulation", "create_app", "run"]


def create_app(*args, **kwargs):
    """Lazy proxy so importing the package doesn't require FastAPI."""
    from src.dashboard.app import create_app as _create_app

    return _create_app(*args, **kwargs)


def run(*args, **kwargs):  # pragma: no cover
    from src.dashboard.app import run as _run

    return _run(*args, **kwargs)
