"""Retrieve node: Taglish → English red-flag concepts → vector search.

The LLM hop is the cross-lingual bridge — a Taglish query reaches the English
corpus through concepts rather than embedding luck. The redacted text is
embedded alongside the concepts so surface matches still count.
"""

from langchain_core.language_models import BaseChatModel

from app.graph.nodes.common import load_prompt, parse_json_reply
from app.graph.state import GraphState
from app.llm import invoke_with_retry
from app.retrieval.store import ChunkStore

TOP_K = 6


def make_retrieve(model: BaseChatModel, store: ChunkStore):
    prompt = load_prompt("retrieve")

    def retrieve(state: GraphState) -> dict:
        reply = invoke_with_retry(
            model,
            prompt.format(
                message_type=state["message_type"],
                redacted_text=state["redacted_text"],
            ),
        )
        try:
            parsed = parse_json_reply(reply.content)
            concepts = [c for c in parsed if isinstance(c, str)][:6]
        except (ValueError, TypeError):
            concepts = []

        chunks = store.search(concepts + [state["redacted_text"]], top_k=TOP_K)
        return {"concepts_en": concepts, "retrieved": chunks}

    return retrieve
