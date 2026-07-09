"""Dataclasses shared across core/, adapters/, and api/.

Kept deliberately free of any provider-specific types (no MCP schema
objects, no Anthropic SDK types) so this module stays importable from
anywhere without dragging in a specific LLM provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Entry:
    id: int | None
    date: str
    raw_text: str
    structured: dict[str, Any]
    tags: list[str]
    archived: bool = False
    created_at: str | None = None


@dataclass
class MetricPoint:
    date: str
    metric_name: str
    value: float


@dataclass
class Goal:
    id: int | None
    metric: str
    start_value: float
    start_date: str
    target_value: float
    target_date: str
    status: str = "active"


@dataclass
class RollupSummary:
    id: int | None
    period_start: str
    period_end: str
    summary: dict[str, Any]
    status: str = "draft"  # draft | approved | rejected | needs_attention
    created_at: str | None = None
    reviewed_at: str | None = None
    reviewer_notes: str | None = None


@dataclass
class SubAgentSpec:
    """Provider-agnostic description of a bounded task. A ClaudeCodeAdapter
    or a future AnthropicAPIAdapter each interpret this the same way, just
    executed differently (Claude Code subagent/Task vs. a scoped API call).
    """
    name: str
    system_prompt: str
    tools: list[str]
    tier: Literal["fast", "capable"]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


def percent_achieved(start_value: float, target_value: float, current_value: float) -> float:
    """Works for both loss goals (start > target) and gain goals
    (start < target) since it's the signed ratio of progress over the
    full span. Clamped to [0, 100] so overshoot or reversal don't produce
    nonsensical percentages.
    """
    span = target_value - start_value
    if span == 0:
        return 100.0
    raw = (current_value - start_value) / span * 100.0
    return max(0.0, min(100.0, raw))
