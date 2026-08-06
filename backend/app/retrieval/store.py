"""Vector search over kb_chunks. The only retrieval surface.

Chunks whose parent is a non-retrievable message example (LEGIT rows, eval
holdouts) are excluded at load, so no query can ever return them. Embeddings
are computed with the local model on first load and written back to the
embedding column; vectors are normalized, so cosine similarity is a dot
product. The KB is under 2,000 rows — full scan in numpy, no index.
"""

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.config import BACKEND_ROOT, get_settings
from app.retrieval.embedder import DIMENSION, embed_passages, embed_queries

KNOWLEDGE_BASE_TREE = BACKEND_ROOT.parent / "knowledge-base"
EMBEDDED_COPY = BACKEND_ROOT / "var" / "kb_embedded.sqlite"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    parent_type: str
    parent_id: str
    source_id: str
    scam_type: str | None


_EXCLUDE_NON_RETRIEVABLE = """
    SELECT c.chunk_id, c.text, c.parent_type, c.parent_id, c.source_id,
           COALESCE(m.scam_type, l.scam_type), c.embedding
    FROM kb_chunks c
    LEFT JOIN message_examples m
           ON c.parent_type = 'message_example' AND c.parent_id = m.message_id
    LEFT JOIN lure_patterns l
           ON c.parent_type = 'lure_pattern' AND c.parent_id = l.pattern_id
    WHERE c.parent_type != 'message_example'
       OR (m.retrievable = 1 AND m.eval_holdout = 0 AND m.label != 'LEGIT')
"""


class ChunkStore:
    def __init__(self, kb_path: Path | None = None):
        self._kb_path = self._writable_path(Path(kb_path or get_settings().kb_path))
        self._chunks: list[Chunk] = []
        self._vectors: np.ndarray | None = None
        self._load()

    @staticmethod
    def _writable_path(kb_path: Path) -> Path:
        # Nian's tree is read-only to us; embeddings are written to a
        # backend-owned copy, refreshed whenever his build is newer.
        if KNOWLEDGE_BASE_TREE not in kb_path.parents:
            return kb_path
        if (not EMBEDDED_COPY.exists()
                or EMBEDDED_COPY.stat().st_mtime < kb_path.stat().st_mtime):
            EMBEDDED_COPY.parent.mkdir(exist_ok=True)
            shutil.copy2(kb_path, EMBEDDED_COPY)
        return EMBEDDED_COPY

    def _load(self) -> None:
        con = sqlite3.connect(self._kb_path)
        try:
            rows = con.execute(_EXCLUDE_NON_RETRIEVABLE).fetchall()
            missing = [(i, r) for i, r in enumerate(rows) if r[6] is None]
            if missing:
                texts = [r[1] for _, r in missing]
                vectors = embed_passages(texts).astype(np.float32)
                con.executemany(
                    "UPDATE kb_chunks SET embedding = ? WHERE chunk_id = ?",
                    [(vec.tobytes(), r[0]) for vec, (_, r) in zip(vectors, missing)],
                )
                con.commit()
                rows = con.execute(_EXCLUDE_NON_RETRIEVABLE).fetchall()
        finally:
            con.close()

        self._chunks = [Chunk(*row[:6]) for row in rows]
        self._vectors = np.array(
            [np.frombuffer(row[6], dtype=np.float32) for row in rows]
        ).reshape(len(rows), DIMENSION)

    def search(self, queries: list[str], top_k: int = 6) -> list[Chunk]:
        if not queries or self._vectors is None or not len(self._chunks):
            return []
        query_vectors = embed_queries(queries)
        # Score each chunk by its best match across the query set: the
        # redacted text and each extracted concept vote independently.
        scores = (query_vectors @ self._vectors.T).max(axis=0)
        order = np.argsort(scores)[::-1][:top_k]
        return [self._chunks[i] for i in order]

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)
