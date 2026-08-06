"""StateGraph wiring. The conditional edge and its bound live here.

The reflection loop is the one place this system could hang, so the
termination rule is spelled out: reflect fires only when confidence is low
AND no reflection has happened yet. Worst case is four LLM calls per request.
"""

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from app.config import get_settings
from app.graph.nodes.advise import make_advise
from app.graph.nodes.detect import make_detect
from app.graph.nodes.retrieve import make_retrieve
from app.graph.state import GraphState
from app.retrieval.store import ChunkStore


def _reflect(state: GraphState) -> dict:
    # Not an LLM call: it re-enters detect, whose prompt then carries the
    # prior verdict and the stated doubt.
    return {"reflection_count": state.get("reflection_count", 0) + 1}


def build_graph(model: BaseChatModel, store: ChunkStore, threshold: float | None = None):
    bound = threshold if threshold is not None else get_settings().confidence_threshold

    def route(state: GraphState) -> str:
        if state["confidence"] >= bound:
            return "advise"
        if state.get("reflection_count", 0) >= 1:
            return "advise"
        return "reflect"

    graph = StateGraph(GraphState)
    graph.add_node("retrieve", make_retrieve(model, store))
    graph.add_node("detect", make_detect(model))
    graph.add_node("reflect", _reflect)
    graph.add_node("advise", make_advise(model))

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "detect")
    graph.add_conditional_edges("detect", route, {"advise": "advise", "reflect": "reflect"})
    graph.add_edge("reflect", "detect")
    graph.add_edge("advise", END)

    return graph.compile()


def initial_state(redacted_text: str, message_type: str, redactions: list[str],
                  output_language: str) -> GraphState:
    return {
        "redacted_text": redacted_text,
        "message_type": message_type,
        "redactions": redactions,
        "output_language": output_language,
        "reflection_count": 0,
        "low_confidence_reason": None,
    }
