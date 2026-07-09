from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_store
from core.memory_store import MemoryStore
from core.models import RollupSummary
from core.review import RollupNotFoundError, approve_rollup, reject_rollup

router = APIRouter()


class ReviewIn(BaseModel):
    reviewer_notes: str | None = None


class RollupOut(BaseModel):
    id: int
    period_start: str
    period_end: str
    summary: dict[str, Any]
    status: str
    reviewer_notes: str | None = None


def _to_out(rollup: RollupSummary) -> RollupOut:
    return RollupOut(
        id=rollup.id,
        period_start=rollup.period_start,
        period_end=rollup.period_end,
        summary=rollup.summary,
        status=rollup.status,
        reviewer_notes=rollup.reviewer_notes,
    )


@router.get("", response_model=list[RollupOut])
def list_rollups(
    status: str | None = None, store: MemoryStore = Depends(get_store)
) -> list[RollupOut]:
    return [_to_out(r) for r in store.list_rollups(status=status)]


@router.get("/{rollup_id}", response_model=RollupOut)
def get_rollup(rollup_id: int, store: MemoryStore = Depends(get_store)) -> RollupOut:
    rollup = store.get_rollup(rollup_id)
    if rollup is None:
        raise HTTPException(status_code=404, detail="rollup not found")
    return _to_out(rollup)


@router.post("/{rollup_id}/approve")
def approve(
    rollup_id: int, payload: ReviewIn, store: MemoryStore = Depends(get_store)
) -> dict[str, str]:
    try:
        approve_rollup(store, rollup_id, reviewer_notes=payload.reviewer_notes)
    except RollupNotFoundError:
        raise HTTPException(status_code=404, detail="rollup not found")
    return {"status": "approved"}


@router.post("/{rollup_id}/reject")
def reject(
    rollup_id: int, payload: ReviewIn, store: MemoryStore = Depends(get_store)
) -> dict[str, str]:
    try:
        reject_rollup(store, rollup_id, reviewer_notes=payload.reviewer_notes)
    except RollupNotFoundError:
        raise HTTPException(status_code=404, detail="rollup not found")
    return {"status": "needs_attention"}
