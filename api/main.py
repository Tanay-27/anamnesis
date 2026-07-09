"""FastAPI app. Kept intentionally thin: routers under /api do the
work, and (from Epoch 7 onward) the frontend is mounted as static files
at root — same origin, no CORS to configure for local use.
"""
from __future__ import annotations

from fastapi import FastAPI

from api.routes import entries, goals, metrics, rollups

app = FastAPI(title="Anamnesis")

app.include_router(entries.router, prefix="/api/entries", tags=["entries"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(rollups.router, prefix="/api/rollups", tags=["rollups"])
