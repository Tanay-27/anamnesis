"""Thin REST routes over MemoryStore/classify — no business logic lives
here. If a route needs more than a few lines, that logic belongs in
core/ instead.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_store
from core.classify import log_entry
from core.memory_store import MemoryStore

router = APIRouter()


class EntryIn(BaseModel):
    date: str
    raw_text: str
    tags: list[str] | None = None
    structured: dict[str, Any] | None = None


class EntryOut(BaseModel):
    id: int
    date: str
    raw_text: str
    structured: dict[str, Any]
    tags: list[str]
    archived: bool


@router.post("", response_model=EntryOut)
def create_entry(payload: EntryIn, store: MemoryStore = Depends(get_store)) -> EntryOut:
    if payload.tags is not None and payload.structured is not None:
        entry_id = store.add_entry(
            date=payload.date,
            raw_text=payload.raw_text,
            structured=payload.structured,
            tags=payload.tags,
        )
    else:
        # No classification supplied (e.g. the plain entry form) — fall
        # back to the rule-based stub rather than requiring the caller
        # to classify it themselves.
        entry_id = log_entry(store, date=payload.date, raw_text=payload.raw_text)

    entries = store.get_entries(
        start_date=payload.date, end_date=payload.date, include_archived=True
    )
    entry = next(e for e in entries if e.id == entry_id)
    return EntryOut(
        id=entry.id,
        date=entry.date,
        raw_text=entry.raw_text,
        structured=entry.structured,
        tags=entry.tags,
        archived=entry.archived,
    )


@router.get("", response_model=list[EntryOut])
def list_entries(
    start_date: str | None = None,
    end_date: str | None = None,
    include_archived: bool = False,
    store: MemoryStore = Depends(get_store),
) -> list[EntryOut]:
    entries = store.get_entries(
        start_date=start_date, end_date=end_date, include_archived=include_archived
    )
    return [
        EntryOut(
            id=e.id,
            date=e.date,
            raw_text=e.raw_text,
            structured=e.structured,
            tags=e.tags,
            archived=e.archived,
        )
        for e in entries
    ]
