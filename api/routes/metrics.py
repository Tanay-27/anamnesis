from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_store
from core.memory_store import MemoryStore

router = APIRouter()


class MetricIn(BaseModel):
    date: str
    metric_name: str
    value: float


class MetricPointOut(BaseModel):
    date: str
    value: float


@router.post("")
def add_metric(payload: MetricIn, store: MemoryStore = Depends(get_store)) -> dict[str, str]:
    store.add_metric(payload.date, payload.metric_name, payload.value)
    return {"status": "ok"}


@router.get("/{metric_name}", response_model=list[MetricPointOut])
def get_metric_series(
    metric_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    store: MemoryStore = Depends(get_store),
) -> list[MetricPointOut]:
    series = store.get_metric_series(metric_name, start_date=start_date, end_date=end_date)
    return [MetricPointOut(date=p.date, value=p.value) for p in series]
