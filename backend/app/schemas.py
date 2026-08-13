"""Request/response models for the API contract in ARCHITECTURE.md."""

from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["SCAM", "LIKELY_SCAM", "UNCLEAR", "LIKELY_LEGIT"]
MessageType = Literal["sms", "email", "url"]
Language = Literal["en", "tl"]


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    language: Language = "tl"


class RedFlag(BaseModel):
    label: str
    detail: str
    chunk_id: str | None = None


class Contact(BaseModel):
    organisation: str
    hotline: str
    url: str


class SimilarScam(BaseModel):
    text: str
    scam_type: str | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    parent_type: str          # message_example | advisory | lure_pattern | brand_rebuttal
    scam_type: str | None = None


class AnalyzeResponse(BaseModel):
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    reflected: bool
    message_type: MessageType
    redactions: list[str]
    redacted_text: str
    red_flags: list[RedFlag]
    explanation: str
    next_steps: list[str]
    contacts: list[Contact]
    similar_scams: list[SimilarScam]
    concepts_en: list[str]
    retrieved: list[RetrievedChunk]
    low_confidence_reason: str | None = None
    kb_freshness: str
    model_id: str


class MetaResponse(BaseModel):
    kb_freshness: str
    model_id: str
    chunk_count: int


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
