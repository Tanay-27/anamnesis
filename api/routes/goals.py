from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_store
from core.memory_store import MemoryStore
from core.models import Goal, percent_achieved

router = APIRouter()


class GoalIn(BaseModel):
    metric: str
    start_value: float
    start_date: str
    target_value: float
    target_date: str


class GoalOut(BaseModel):
    id: int
    metric: str
    start_value: float
    start_date: str
    target_value: float
    target_date: str
    status: str
    percent_achieved: float | None = None


def _current_value(store: MemoryStore, metric: str) -> float | None:
    series = store.get_metric_series(metric)
    return series[-1].value if series else None


def _to_out(store: MemoryStore, goal: Goal) -> GoalOut:
    current = _current_value(store, goal.metric)
    pct = (
        percent_achieved(goal.start_value, goal.target_value, current)
        if current is not None
        else None
    )
    return GoalOut(
        id=goal.id,
        metric=goal.metric,
        start_value=goal.start_value,
        start_date=goal.start_date,
        target_value=goal.target_value,
        target_date=goal.target_date,
        status=goal.status,
        percent_achieved=pct,
    )


@router.post("", response_model=GoalOut)
def create_goal(payload: GoalIn, store: MemoryStore = Depends(get_store)) -> GoalOut:
    goal = Goal(
        id=None,
        metric=payload.metric,
        start_value=payload.start_value,
        start_date=payload.start_date,
        target_value=payload.target_value,
        target_date=payload.target_date,
    )
    goal_id = store.add_goal(goal)
    goal.id = goal_id
    return _to_out(store, goal)


@router.get("", response_model=list[GoalOut])
def list_goals(
    status: str | None = None, store: MemoryStore = Depends(get_store)
) -> list[GoalOut]:
    return [_to_out(store, g) for g in store.get_goals(status=status)]
