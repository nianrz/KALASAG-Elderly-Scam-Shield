"""Embedding generation — NOT RUN.

The LLM provider is unresolved (open question 2 in the canonical plan) and
the Accenture Bedrock sandbox model list is unconfirmed. Populating the
embedding column requires choosing a provider, which is not this
deliverable's decision to make.

To use this script:
  1. Pick a provider and an embedding model.
  2. Set EMBEDDING_DIM in kb/db.py and vector(N) in the Postgres schema
     to that model's dimension.
  3. Implement embed_batch() below.
  4. Run: knowledge-base/.venv/bin/python knowledge-base/scripts/embed.py

Cross-lingual note: the corpus is Taglish and the advisories are English.
Mitigation 3 (bilingual keyword fields) is already applied to every chunk.
Mitigations 1 and 2 remain open — see HANDOFF-allen.md.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BATCH_SIZE = 64


def embed_batch(texts: list[str]) -> list[list[float]]:
    raise NotImplementedError(
        "No embedding provider chosen. See the module docstring and HANDOFF-allen.md."
    )


def main() -> int:
    db_path = ROOT / "out" / "kb.sqlite"
    conn = sqlite3.connect(db_path)
    pending = conn.execute(
        "SELECT COUNT(*) FROM kb_chunks WHERE embedding IS NULL"
    ).fetchone()[0]
    print(f"{pending} chunks awaiting embeddings.")
    print("No provider configured — nothing to do. This is expected.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
