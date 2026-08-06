"""Detect node: verdict + confidence + red flags, guardrail rules in prompt.

On a reflection pass the prompt carries the prior verdict, its confidence,
and the stated doubt — the mentor's ruling that retry must differ from a
plain re-run.
"""

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from app.graph.nodes.common import load_prompt, parse_json_reply
from app.graph.state import GraphState
from app.llm import invoke_with_retry
from app.schemas import RedFlag, Verdict


class DetectOutput(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    red_flags: list[RedFlag]
    low_confidence_reason: str | None = None


def _render_chunks(state: GraphState) -> str:
    chunks = state.get("retrieved", [])
    if not chunks:
        return "(the knowledge base returned nothing for this message)"
    return "\n\n".join(
        f"[{c.chunk_id}] ({c.parent_type})\n{c.text}" for c in chunks
    )


def make_detect(model: BaseChatModel):
    prompt = load_prompt("detect")
    reflect_prompt = load_prompt("reflect")

    def detect(state: GraphState) -> dict:
        rendered = prompt.format(
            retrieved_chunks=_render_chunks(state),
            message_type=state["message_type"],
            redactions=state["redactions"] or "none",
            redacted_text=state["redacted_text"],
        )
        if state.get("reflection_count", 0) > 0:
            rendered += "\n\n" + reflect_prompt.format(
                prior_verdict=state["verdict"],
                prior_confidence=state["confidence"],
                low_confidence_reason=state.get("low_confidence_reason") or "not stated",
            )

        reply = invoke_with_retry(model, rendered)
        output = DetectOutput.model_validate(parse_json_reply(reply.content))
        return {
            "verdict": output.verdict,
            "confidence": output.confidence,
            "red_flags": output.red_flags,
            "low_confidence_reason": output.low_confidence_reason,
        }

    return detect
