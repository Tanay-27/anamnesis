# Anamnesis — Implementation Plan

Tiered agent memory for personal health tracking. Working memory (live
session) → eager index (recent ~15 days, compact JSON) → long-term rollup
(fortnightly, audit-and-retain), with a human review checkpoint before
anything gets promoted or archived.

## Module layout

```
core/           pure business logic — no I/O beyond the DB, fully
                unit-testable without any LLM. Never imports from
                adapters/ or api/.
  models.py         dataclasses: Entry, Goal, RollupSummary, SubAgentSpec
  memory_store.py   SQLite wrapper — the ONLY file with raw SQL
  classify.py       classify_and_compress logic
  rollup.py         audit_and_retain_rollup logic
  schema.sql
  migrate.py

adapters/
  claude_code/
    mcp_server.py   MCP tools wrapping core/ functions
    hooks/          shell scripts for Claude Code lifecycle hooks

api/
  main.py           FastAPI app
  routes/{entries,metrics,goals,rollups}.py

frontend/
  index.html, dashboard.html
  js/{api.js, charts.js}   ECharts with dataZoom for scroll/zoom

tests/
```

Dependency direction is one-way: `core/` never imports `adapters/` or
`api/`. If that boundary gets crossed, logic has leaked out of core.

## Design principles

- **Raw daily entries are never deleted**, only archived after an
  approved rollup — the safety net against rollup drift.
- **Numeric fields (weight, protein, steps) are aggregated in plain
  Python**, never re-summarized by an LLM. Only qualitative fields go
  through the model.
- **Rollups are drafts until a human approves them.** No silent
  auto-promotion.
- Multi-label tagging (nutrition/sleep/workout) — an entry can carry
  several tags, not forced into one category.

## Epochs

Each epoch has a test gate that must be green before moving to the next.

0. **Scaffold** — repo structure, schema.sql, migrate.py, pytest config.
   Gate: migration produces all six tables with expected columns. ✅
1. **MemoryStore** — CRUD for all tables. Pure unit tests, zero LLM.
2. **classify_and_compress stub** — rule-based, proves the plumbing
   before any LLM involvement.
3. **Claude Code MCP adapter** — `log_update`, `get_eager_index`,
   `search_memory` tools. Swap stub for real prompt-driven classification.
   Manual test: live Claude Code session, inspect DB for sane output.
4. **Rollup logic** — deterministic numeric aggregation + LLM-driven
   qualitative diff (promoted / dropped / carried_forward).
5. **Human review + archiving** — CLI approve/reject. Approve archives
   source entries + writes a memory_versions snapshot. Reject leaves
   data untouched.
6. **FastAPI REST layer** — thin routes over MemoryStore, no logic in
   the routes themselves.
7. **Frontend: entry form + list.**
8. **Frontend: ECharts dashboard** — weight / steps / goal % with
   dataZoom for scroll/zoom.
9. **Frontend: rollup review UI** — same backend logic as Epoch 5,
   just a second frontend on it.
10. **Hardening** — error handling, provider-selection config seam,
    full week-in-the-life walkthrough.
11. *(later, optional)* **Tauri wrap** — native-feeling packaging of
    the same frontend, no rewrite.

## Provider abstraction note

Claude Code (via MCP + hooks) is the only provider implemented right
now. The provider-agnostic seam is `core/` itself being pure functions
with no adapter-specific imports — a future `AnthropicAPIAdapter` or
`OpenAICompatAdapter` would wrap the same `core/` functions differently,
not reimplement them. Don't build those adapters speculatively before
a second real provider is actually needed.
