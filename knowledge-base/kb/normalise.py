"""Text normalisation and eval-set holdout matching.

The holdout rule is exact-or-prefix over an aggressive identity key, not
over display text. Two reasons, both measured against the corpus:

  * The eval-set CSV truncated message text at 400 characters; five rows
    hit that cap and are strict prefixes of longer messages still present
    in the corpus. Exact matching alone lets all five leak.
  * Corpus messages drift by whitespace and punctuation around an
    identical template. msg01483 and msg01484 differ by a single space
    before the URL; under a whitespace-preserving key neither is a prefix
    of the other, so msg01484 stayed retrievable while its twin was the
    eval set's M010.

Letting either through lets the Detector retrieve the answers to its own
evaluation. See pipeline invariant 5 in CLAUDE.md.
"""

from __future__ import annotations

import re
from typing import Iterable

_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"^[\s.!?,;:\-–—'\"]+|[\s.!?,;:\-–—'\"]+$")

# Characters that carry identity. Latin and Cyrillic both appear in the
# corpus — scammers use Cyrillic homoglyph domains (9910.омск.рус).
_NON_IDENTITY = re.compile(r"[^0-9a-zЀ-ӿ]+")

# Below this length a prefix match is too weak to be evidence of identity.
# Lower than the display-text equivalent because identity_key strips
# characters: 24 characters of prose is roughly 20 of key.
MIN_KEY_LEN = 20


def normalise_text(text: str) -> str:
    """Lowercase, collapse internal whitespace, strip surrounding punctuation."""
    if text is None:
        return ""
    collapsed = _WHITESPACE.sub(" ", str(text)).strip().lower()
    return _EDGE_PUNCT.sub("", collapsed)


def identity_key(text: str) -> str:
    """Aggressive key for 'is this the same message?'.

    Lowercases and drops everything that is not alphanumeric, so the same
    message survives whitespace jitter, punctuation drift, and re-wrapping.
    Holdout matching only — never for display or storage.
    """
    if text is None:
        return ""
    return _NON_IDENTITY.sub("", str(text).lower())


def holdout_index(eval_texts: Iterable[str]) -> list[str]:
    """Identity keys of the eval set, de-duplicated, non-trivial, longest first."""
    keys = {identity_key(t) for t in eval_texts}
    usable = {k for k in keys if len(k) >= MIN_KEY_LEN}
    return sorted(usable, key=len, reverse=True)


def is_held_out(candidate: str, eval_norms: list[str]) -> bool:
    """True if candidate equals, or begins with, any eval-set message."""
    key = identity_key(candidate)
    if not key:
        return False
    return any(key == e or key.startswith(e) for e in eval_norms)
