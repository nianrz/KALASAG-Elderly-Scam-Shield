"""Near-duplicate detection over the retrievable pool.

The corpus carries template families: 14 near-identical "earn 500P watching
YouTube" messages, 9 "[ BANCO DE ORO ] account restricted" variants. Exact
deduplication in build_kb.py does not catch them because they differ by a
word, a digit, or a domain. As retrieval targets they are redundant — several
top-k slots spent on variants of one message means the Detector sees six
chunks carrying two or three distinct pieces of evidence.

Similarity is Jaccard over character shingles of the identity key, so the
comparison ignores the whitespace and punctuation drift that distinguishes
most variants.
"""

from __future__ import annotations

from typing import Iterable

from kb.normalise import identity_key

SHINGLE_SIZE = 5

# Measured against the corpus: at 0.8, clusters are template families that
# differ by an amount, a domain, or a greeting. Lower starts merging distinct
# lures that share boilerplate.
SIMILARITY_THRESHOLD = 0.8


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[str]:
    """Character n-grams of the identity key."""
    key = identity_key(text)
    if not key:
        return set()
    if len(key) <= size:
        return {key}
    return {key[i:i + size] for i in range(len(key) - size + 1)}


def similarity(left: str, right: str) -> float:
    """Jaccard similarity of two messages, 0.0 to 1.0."""
    a, b = shingles(left), shingles(right)
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    return intersection / (len(a) + len(b) - intersection)


def redundant_ids(items: Iterable[tuple[str, str]]) -> set[str]:
    """IDs to withhold from retrieval: every near-duplicate but one per cluster."""
    pairs = list(items)
    grams = {item_id: shingles(text) for item_id, text in pairs}
    parent = {item_id: item_id for item_id, _ in pairs}

    def find(item_id: str) -> str:
        while parent[item_id] != item_id:
            parent[item_id] = parent[parent[item_id]]
            item_id = parent[item_id]
        return item_id

    for i, (left_id, _) in enumerate(pairs):
        for right_id, _ in pairs[i + 1:]:
            a, b = grams[left_id], grams[right_id]
            if not a or not b:
                continue
            intersection = len(a & b)
            if intersection / (len(a) + len(b) - intersection) >= SIMILARITY_THRESHOLD:
                left_root, right_root = find(left_id), find(right_id)
                if left_root != right_root:
                    parent[left_root] = right_root

    texts = dict(pairs)
    clusters: dict[str, list[str]] = {}
    for item_id, _ in pairs:
        clusters.setdefault(find(item_id), []).append(item_id)

    redundant = set()
    for members in clusters.values():
        # Longest text wins — it carries the most detail a query could match.
        # The id breaks ties so the build is reproducible.
        ordered = sorted(members, key=lambda m: (-len(texts[m]), m))
        redundant.update(ordered[1:])
    return redundant
