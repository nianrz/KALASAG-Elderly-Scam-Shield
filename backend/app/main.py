"""FastAPI app: POST /api/analyze, GET /api/health, GET /api/meta.

Errors return {"error": {"code", "message"}} with user-safe text. Provider
errors never echo the request body — that would leak the input preprocessing
exists to protect.
"""

import logging
import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.preprocess import preprocess
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Contact,
    MetaResponse,
    RedFlag,
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
    logger.error("analysis failed: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "ANALYSIS_FAILED",
                           "message": "Something went wrong. Please try again."}},
    )


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

    # Stubbed graph — replaced in T13 by the real LangGraph pipeline.
    return AnalyzeResponse(
        verdict="SCAM",
        confidence=0.91,
        reflected=False,
        message_type=pre.message_type,
        redactions=pre.redactions,
        red_flags=[
            RedFlag(
                label="Claims your account is on hold",
                detail="Real suspensions appear when you log in, not as a text with a link.",
                chunk_id="lure-account-suspended",
            )
        ],
        explanation="Scam po ito. Ginagaya ng mensahe ang bangko para kunin ang login mo.",
        next_steps=[
            "Huwag i-click ang link.",
            "I-block at i-delete ang mensahe.",
        ],
        contacts=[
            Contact(organisation="Inter-Agency Response Center (I-ARC)", hotline="1326",
                    url="https://www.cybersecurity.ph/cybercrime-reporting/"),
        ],
        similar_scams=[
            SimilarScam(
                text="BDO ALERT Your online access is suspended. Reactivate here bdo-verify.xyz/login",
                scam_type="bank-impersonation",
            )
        ],
        kb_freshness=freshness,
        model_id=settings.model_id,
    )
