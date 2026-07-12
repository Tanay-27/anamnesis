# Agent Memory in Anamnesis

This is the concept the whole project exists to practice: an agent that
runs for months without blowing up its context window, without losing
detail, and without silently drifting. Below is what we actually built,
how it maps to the theory, and exactly what's stored where and exposed
to the agent when.

## The problem this solves

An LLM's context window is expensive and finite; a health-tracking
agent's history is unbounded (it should run for years). The whole
design is about controlling what's *in context* on any given turn vs.
what's *addressable* — fetched only when relevant — rather than ever
loading "everything that ever happened."

## The three tiers

| Tier | What it is | Where it lives | Lifetime |
|---|---|---|---|
| **Working memory** | The live conversation itself | Claude Code's own session state | One session |
| **Eager index** | Recent, compact, structured entries | `daily_entries` (non-archived rows) | Until rolled up |
| **Long-term memory** | Consolidated summaries | `rollup_summaries` (approved) | Forever |

Nothing carries over between sessions except what's explicitly
persisted — the whole point of a stateless store behind the agent,
rather than trusting a growing conversation transcript.

## What's stored, concretely

| Table | Holds | Written by |
|---|---|---|
| `daily_entries` | raw text + structured JSON + `archived` flag | `log_update` (agent-classified) |
| `entry_tags` | multi-label tags (workout/sleep/nutrition/general) | same — one entry, several tags, not exclusive |
| `daily_metrics` | long-format numeric time series (weight, steps, ...) | logged alongside entries, independent of them |
| `goals` | start/target value + date per metric | set once, read continuously |
| `rollup_summaries` | `{numeric_metrics, promoted, dropped, carried_forward}` + status | `audit_and_retain_rollup`, then a human |
| `memory_versions` | append-only snapshot per mutation | every approve/reject |

## Lifecycle: raw log → long-term memory

1. **You log something.** The agent (Claude Code) reads your raw text
   and classifies it *itself* — tags and structured fields — before
   ever calling a tool. The MCP tool's description is effectively the
   "prompt" that teaches this; `core/classify.py`'s rule-based version
   only exists as a stub/fallback, not what a real session uses.
2. **`log_update` persists it** into `daily_entries` — nothing
   summarized yet, this is the raw material.
3. **The eager index is just a query**, not a separate write path:
   `get_eager_index` returns the recent, non-archived window as
   compact JSON. This is what the agent loads at the start of a
   session instead of re-reading full history.
4. **Rollup time** (`audit_and_retain_rollup`): numeric fields (weight,
   steps, ...) are aggregated in **plain Python** — min/max/avg/trend —
   never re-summarized by an LLM, so a number can't drift or quietly
   vanish. Only the qualitative side (what mattered, what's noise, what
   carries forward) goes through a reasoner — and that reasoner is
   *injected*, not hardcoded, so in production it's Claude Code's own
   reasoning, and in tests it's a stub.
5. **The rollup lands as a draft**, `status="draft"` — nothing is
   promoted automatically.
6. **A human reviews it** (`core/review.py`, or the review UI):
   *approve* archives the source entries in that date window (flag
   only — never deleted) and snapshots the decision into
   `memory_versions`; *reject* leaves everything untouched and marks
   `needs_attention`. This is the checkpoint against silent drift —
   the exact failure mode we saw happen live when a manually-written
   continuity brief needed three rounds of correction before it was
   right.

## What's available to the agent, and when

- **Every session**: `get_eager_index` (recent structured window) and
  `search_memory` (keyword search, including archived/rolled-up
  entries) — both callable on demand, not preloaded into context.
- **While logging**: nothing beyond the current message — classification
  is the agent's own reasoning, not a lookup.
- **While rolling up**: the *numbers* are handed to the reasoner
  already aggregated (it never re-derives them); the *entries* are
  handed as formatted text for the qualitative judgment call only.
- **Nothing is ever force-loaded.** A long-idle app with years of
  history costs the same first-turn context as a brand-new one — only
  the eager index (recent window) and whatever a tool call fetches
  ever enter the conversation.

## Design principles (the "why" behind each choice)

- **Archive, never delete.** If a rollup is wrong, the source is still
  there to regenerate from — the hard safety net against drift.
- **Numbers are code, not prose.** Deterministic aggregation removes an
  entire class of hallucination/drift risk that a "summarize the last
  two weeks" LLM prompt would carry.
- **Multi-label, not exclusive categories.** A day can be workout *and*
  sleep *and* nutrition at once — forcing one tag loses the
  cross-cutting signal that's often the most useful part.
- **Drafts require approval.** Nothing is promoted to long-term memory
  silently, no matter how good the reasoner is.
- **Malformed reasoning fails loudly.** `RollupReasoningError` — a
  broken or garbled rollup attempt never persists a corrupt draft that
  looks legitimate in the review queue.

## Mapping back to the original theory

| Concept from the design discussion | What it became here |
|---|---|
| Working memory | Claude Code's live session |
| Eager index / short-term buffer | `daily_entries` (non-archived) via `get_eager_index` |
| Long-term consolidation | `rollup_summaries` (approved) |
| Audit / confidence tracking | `memory_versions` |
| Retrieval-on-demand vs. always-loaded | Tools (`get_eager_index`, `search_memory`), never preloaded |
| Human-in-the-loop guard against drift | `core/review.py` approve/reject |
