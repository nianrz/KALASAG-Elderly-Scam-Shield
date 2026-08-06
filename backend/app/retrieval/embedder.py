"""Local sentence-transformer, loaded once and cached.

intfloat/multilingual-e5-small, 384-dim. e5 models are trained with
"query:" / "passage:" prefixes; embedding without them degrades retrieval.
No network after the first download, which is why this is not the chat
provider — switching LLM_MODEL must never force a KB re-embed.
"""

from functools import lru_cache

import numpy as np

MODEL_NAME = "intfloat/multilingual-e5-small"
DIMENSION = 384


@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_queries(texts: list[str]) -> np.ndarray:
    return _model().encode(
        [f"query: {t}" for t in texts], normalize_embeddings=True
    )


def embed_passages(texts: list[str]) -> np.ndarray:
    return _model().encode(
        [f"passage: {t}" for t in texts], normalize_embeddings=True
    )
