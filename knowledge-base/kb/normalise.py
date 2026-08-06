"""Text normalisation and eval-set holdout matching.

The holdout rule is exact-or-prefix, not exact. The eval-set CSV truncates
message text at 400 characters; five rows hit that cap and are strict
prefixes of longer messages still present in the corpus. Exact matching
alone lets all five leak into the retrievable pool, which would let the
Detector retrieve the answers to its own evaluation.
"""

from __future__ import annotations

import re
from typing import Iterable

_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"^[\s.!?,;:\-–—'\"]+|[\s.!?,;:\-–—'\"]+$")

# Below this length a prefix match is too weak to be evidence of identity.
MIN_PREFIX_LEN = 24


def normalise_text(text: str) -> str:
    """Lowercase, collapse internal whitespace, strip surrounding punctuation."""
    if text is None:
        return ""
    collapsed = _WHITESPACE.sub(" ", str(text)).strip().lower()
    return _EDGE_PUNCT.sub("", collapsed)


def holdout_index(eval_texts: Iterable[str]) -> list[str]:
    """Normalised, de-duplicated, non-trivial eval texts, longest first."""
    seen = {normalise_text(t) for t in eval_texts}
    usable = {t for t in seen if len(t) >= MIN_PREFIX_LEN}
    return sorted(usable, key=len, reverse=True)


def is_held_out(candidate: str, eval_norms: list[str]) -> bool:
    """True if candidate equals, or begins with, any eval text."""
    norm = normalise_text(candidate)
    if not norm:
        return False
    return any(norm == e or norm.startswith(e) for e in eval_norms)
