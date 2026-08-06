"""GraphState. The raw unredacted input is never in here — that is a privacy
requirement enforced by construction, not by remembering to strip it later."""

from typing import Literal, TypedDict

from pydantic import BaseModel

from app.retrieval.contacts import ReportingContact
from app.retrieval.store import Chunk
from app.schemas import Contact, RedFlag, Verdict


class Advice(BaseModel):
    explanation: str
    next_steps: list[str]
    contacts: list[Contact]


class GraphState(TypedDict, total=False):
    redacted_text: str
    message_type: Literal["sms", "email", "url"]
    redactions: list[str]              # labels only, never values
    output_language: Literal["en", "tl"]

    concepts_en: list[str]             # retrieve
    retrieved: list[Chunk]             # retrieve

    verdict: Verdict                   # detect
    confidence: float                  # detect
    first_verdict: Verdict             # detect, first pass only — eval reads it
    first_confidence: float            # detect, first pass only
    red_flags: list[RedFlag]           # detect
    reflection_count: int              # detect
    low_confidence_reason: str | None  # detect → reflect

    advice: Advice                     # advise


__all__ = ["Advice", "Chunk", "GraphState", "RedFlag", "ReportingContact"]
