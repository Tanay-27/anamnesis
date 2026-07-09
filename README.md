# Anamnesis

Tiered agent memory for personal health tracking — daily logs get
classified and compressed into a compact "eager index," which is
periodically rolled up into long-term memory with a human review
checkpoint before anything is promoted or archived.

See `PLAN.md` for the full architecture and epoch-by-epoch build plan.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```
