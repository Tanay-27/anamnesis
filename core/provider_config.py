"""Provider selection seam. Only Claude Code (via the MCP adapter) is
implemented right now — this module exists so that choosing a provider
is a config change (an env var), not a code change, once a second
provider (raw Anthropic API, an OpenAI-compatible endpoint, a local
model) is actually needed. Don't add entries here speculatively; add
one when a second adapter actually gets built.
"""
from __future__ import annotations

import os
from enum import Enum


class Provider(str, Enum):
    CLAUDE_CODE = "claude_code"


def get_active_provider() -> Provider:
    value = os.environ.get("ANAMNESIS_PROVIDER", Provider.CLAUDE_CODE.value)
    try:
        return Provider(value)
    except ValueError:
        available = [p.value for p in Provider]
        raise ValueError(f"Unknown ANAMNESIS_PROVIDER={value!r}. Available: {available}") from None
