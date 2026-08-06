"""FastAPI app: POST /api/analyze, GET /api/health, GET /api/meta.

Errors return {"error": {"code", "message"}} with user-safe text. Provider
errors never echo the request body — that would leak the input preprocessing
exists to protect.
"""

import logging
import sqlite3
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.graph.build import build_graph, initial_state
from app.llm import get_model
from app.preprocess import preprocess
from app.retrieval.store import ChunkStore
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    MetaResponse,
    SimilarScam,
)

logger = logging.getLogger("kalasag")

app = FastAPI(title="Kalasag")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_REQUEST",
                           "message": "Please paste a message first."}},
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    # Type name only — exception text from a provider can echo the input.
    logger.error("analysis failed: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "ANALYSIS_FAILED",
                           "message": "Something went wrong. Please try again."}},
    )


@lru_cache
def get_graph():
    return build_graph(get_model(), ChunkStore())


def _kb_meta() -> tuple[str, int]:
    settings = get_settings()
    con = sqlite3.connect(settings.kb_path)
    try:
        freshness = con.execute("SELECT MAX(retrieved_at) FROM sources").fetchone()[0]
        chunks = con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
    finally:
        con.close()
    return freshness or "", chunks


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
async def meta() -> MetaResponse:
    freshness, chunks = _kb_meta()
    return MetaResponse(
        kb_freshness=freshness,
        model_id=get_settings().model_id,
        chunk_count=chunks,
    )


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    pre = preprocess(request.text)
    freshness, _ = _kb_meta()

    state = get_graph().invoke(initial_state(
        redacted_text=pre.redacted_text,
        message_type=pre.message_type,
        redactions=pre.redactions,
        output_language=request.language,
    ))

    advice = state["advice"]
    similar = [
        SimilarScam(text=chunk.text, scam_type=chunk.scam_type)
        for chunk in state.get("retrieved", [])
        if chunk.parent_type == "message_example"
    ][:3]

    return AnalyzeResponse(
        verdict=state["verdict"],
        confidence=state["confidence"],
        reflected=state.get("reflection_count", 0) > 0,
        message_type=pre.message_type,
        redactions=pre.redactions,
        redacted_text=pre.redacted_text,
        red_flags=state.get("red_flags", []),
        explanation=advice.explanation,
        next_steps=advice.next_steps,
        contacts=advice.contacts,
        similar_scams=similar,
        kb_freshness=freshness,
        model_id=settings.model_id,
    )
