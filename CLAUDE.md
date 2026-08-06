# Elderly Scam Shield

STSP001 capstone. A web app where an elderly Filipino or their caregiver pastes a suspicious SMS, email, or URL and gets **verdict → explanation → next steps** in plain Filipino/Taglish or English, produced by a LangGraph pipeline over a curated Philippine scam knowledge base.

**Presentation is one week out.** Scope decisions favour a working local demo over polish. Do not add features that were not asked for.

## Docs

| File | What it settles |
|---|---|
| `docs/PRD.md` | Scope, users, requirements, success criteria |
| `docs/ARCHITECTURE.md` | Graph shape, state, API contract, module boundaries |
| `docs/DESIGN.md` | UI/UX spec, accessibility rules, EN/TL copy |
| `docs/TASKS.md` | Ordered build tasks with verification steps |
| `docs/capstone-elderly-scam-shield.md` | Canonical proposal (source of truth for scope) |
| `docs/2026-07-29-capstone-mentor-consultation.md` | Mentor rulings — do not contradict these without saying so |

## Directory ownership

Work in your own directory. Branch as `branch/<name>`, merge to `main` daily.

| Path | Owner |
|---|---|
| `backend/` | Aki (Lead), Allen (Tech) |
| `frontend/` | James (UX) |
| `knowledge-base/` | Nian (Domain) — **incoming subtree, do not author here** |
| `docs/` | Lui (Scribe) |

`knowledge-base/` is Nian's deliverable and arrives from his machine. Read `knowledge-base/out/kb.sqlite`; never edit its contents. Until it lands, the backend runs against `backend/tests/fixtures/kb_fixture.sqlite`.

## Stack

- **Backend** — Python 3.14, `uv`, FastAPI, LangGraph, SQLite, `sentence-transformers`
- **Frontend** — Vite + React + TypeScript + Tailwind
- **Tests** — pytest (backend), Vitest (frontend)

Use `uv` for every Python dependency operation. Never `pip install`.

## LLM provider — read before touching `backend/app/llm.py`

The model is swappable by env var. All model access goes through `llm.py`; no other module imports a provider SDK.

```
SHIELD_MODEL=anthropic:claude-opus-5     # default
SHIELD_MODEL=anthropic:claude-sonnet-5   # cheaper, $2/$10 per MTok intro through 2026-08-31
SHIELD_MODEL=google_genai:gemini-...     # free tier
SHIELD_MODEL=bedrock_converse:...        # Accenture sandbox
```

**Never pass `temperature`, `top_p`, `top_k`, or `budget_tokens` to a Claude 5 model.** All four return HTTP 400 on `claude-opus-5` and `claude-sonnet-5`. LangChain's `ChatAnthropic` accepts them without complaint and the failure only appears at request time. Steer behaviour with the prompt, not with sampling parameters.

Thinking is on by default on `claude-opus-5`. `max_tokens` caps thinking *plus* response text, so leave headroom or responses truncate mid-answer.

**Embeddings are not the chat provider.** Retrieval uses a local `sentence-transformers` model with a fixed 384 dimension. Switching `SHIELD_MODEL` must never require re-embedding the KB.

## Pipeline invariants

These are load-bearing. Breaking one is a correctness bug, not a style choice.

1. **Raw user input never enters graph state and is never logged.** `preprocess.py` redacts OTPs, account numbers, card numbers, phone numbers, and emails before anything reaches an LLM. Only redacted text moves forward.
2. **Hotlines and official URLs are read by key, never retrieved semantically.** They come from `brand_rebuttals` and `reporting_contacts` and are passed to the Advisor as data. A fuzzy-matched hotline handed to a panicking user is the one failure this product cannot survive.
3. **The Detector never claims certainty.** There is no `SAFE` verdict. Even `LIKELY_LEGIT` renders with "verify independently before acting."
4. **The self-reflection loop is bounded at one pass.** A loop that cannot terminate is a demo failure.
5. **Eval-set messages are held out of retrieval.** `eval-set-candidate-55.csv` is the test; retrieving it means measuring nothing.

## Prompts

Prompts live in `backend/app/prompts/*.md`, not as string literals. They are the product logic — treat edits to them as code changes and run the eval after.

The Advisor targets **plain Filipino/Taglish, not formal Tagalog**. A model told to "reply in Tagalog" drifts toward textbook register (*panganib*, *pagpapatunay*) that is harder to read than Taglish. Specify register explicitly.

## Conventions

- Match surrounding style. No comments unless the *why* is non-obvious.
- Every feature gets unit tests. Keep them passing.
- Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- No `Co-Authored-By` trailers.
