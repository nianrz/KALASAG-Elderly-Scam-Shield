# Kalasag — Elderly Scam Shield

Paste a suspicious SMS, email, or URL and get a verdict, a plain-language explanation of the red flags, and concrete next steps — in Filipino/Taglish or English.

*Kalasag* is the shield carried by pre-colonial Filipino warriors. It appears on the seal of the Philippine National Police — the agency this app tells users to report to.

STSP001 capstone, AY2526-T3. A LangGraph pipeline over a curated Philippine scam knowledge base.

```
paste → preprocess (redact PII) → retrieve → detect ⇄ reflect → advise → verdict
```

---

## What you need to install

Only install what your role needs. Nobody needs all three.

| Role | Needs |
|---|---|
| Backend (Aki, Allen) | `uv`, Python 3.14 |
| Frontend (James) | Node 20+ |
| QA / E2E (Aki) | Node 20+ (Cypress installs its own browser) |
| Knowledge base (Nian) | Python 3.14 — see `knowledge-base/README.md` |
| Docs (Lui) | Nothing. A text editor. |

**We are not using Docker.** `uv` pins and installs the Python version itself, which covers the part Docker would have solved, and only two of us run the backend. Reconsider if we ever deploy.

### macOS

```bash
brew install uv node
```

### Windows

```powershell
winget install --id=astral-sh.uv
winget install --id=OpenJS.NodeJS.LTS
```

### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Node 20+ from your package manager or https://nodejs.org
```

Check you have them:

```bash
uv --version     # 0.11+
node --version   # v20+
```

You do **not** need to install Python yourself — `uv sync` downloads the right version if it is missing.

---

## Setup

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# open .env and paste in the Accenture sandbox Bedrock token as
# AWS_BEARER_TOKEN_BEDROCK — ask Aki for the current one
uv run uvicorn app.main:app --reload --port 8000
```

`.env.example` is the committed template listing every variable. `.env` is yours, holds the actual key, and is **gitignored and must stay that way** — a key committed once lives in git history forever and the only real fix is rotating it. If you add a new setting, add it to `.env.example` too, or the next person's setup breaks silently.

**The first run downloads about 590MB** — roughly 470MB of PyTorch and friends into `backend/.venv`, plus a ~120MB embedding model into `~/.cache/huggingface`. On a slow connection this takes a while. **Do it today, not on presentation morning.**

Warm start after that is about 13 seconds, because the embedding model loads at boot. That load happens once at FastAPI startup, never per request.

### Frontend

```bash
cd frontend
npm install
npm run dev              # http://localhost:5173
```

Vite proxies `/api/*` to `localhost:8000`, so run the backend too. There is no CORS config to get wrong.

### QA

```bash
cd qa
npm install              # pulls the Cypress binary, ~250MB, one time
```

---

## Running things

```bash
# backend
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd backend && uv run pytest

# frontend
cd frontend && npm run dev
cd frontend && npm test          # Vitest, component tests

# E2E
cd qa && npm run e2e             # stubbed suite, starts the frontend for you
cd qa && npm run cy:open         # interactive runner
cd qa && npm run e2e:smoke       # LIVE — needs the backend and a provider key

# evaluation
cd backend && uv run python eval/run_eval.py
```

The stubbed E2E suite needs no provider key and no network. Only `e2e:smoke` does — it costs real tokens, so run it deliberately.

---

## Configuration

`backend/.env` — copy from `backend/.env.example`:

| Variable | Default | |
|---|---|---|
| `LLM_MODEL` | `bedrock_converse:global.anthropic.claude-sonnet-5` | Any `init_chat_model` string; the `global.` prefix is required from ap-southeast-1 |
| `LLM_MAX_TOKENS` | `4096` | May bound reasoning as well as visible output |
| `CONFIDENCE_THRESHOLD` | `0.70` | Set from the eval sweep, not asserted |
| `LLM_RETRY_BACKOFF` | `20` | Seconds to wait after a 429 |
| `KB_PATH` | real KB if built, else fixture | `knowledge-base/out/kb.sqlite` is picked up automatically once built |

### Getting a key — we pay for nothing

**AWS Bedrock (Accenture sandbox) — the only provider.** Set `AWS_BEARER_TOKEN_BEDROCK` (the `_BEDROCK` suffix is required — botocore looks for that exact name) and `AWS_REGION=ap-southeast-1`. The sandbox serves Claude on AWS billing; it costs us nothing.

Gemini support was removed on 2026-08-06 once the sandbox was verified live — re-adding a provider is an `uv add` of its langchain package plus an `LLM_MODEL` string.

> A Claude Pro/Max subscription does **not** cover API calls — that's claude.ai and Claude Code only. We deliberately depend on no paid API key.

A full eval run is about 200 calls and the sandbox's rate limits are undocumented. `llm.py` retries with backoff on 429, so an eval run slows down rather than failing.

Switching providers requires no code change and no re-embedding: embeddings are local and provider-independent by design.

**Never commit `.env`.** It is gitignored; keep it that way.

---

## Layout

```
backend/     FastAPI + LangGraph pipeline, pytest        Aki, Allen
frontend/    Vite + React + TS + Tailwind, Vitest        James
qa/          Cypress E2E + test plan                     Aki
knowledge-base/  Scam corpus and advisories (read-only)  Nian
docs/        PRD, architecture, design, tasks            Lui
```

## Docs

Read `CLAUDE.md` first — conventions, ownership, and the pipeline invariants that are correctness requirements rather than style.

| File | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Conventions, ownership, invariants, doc-maintenance rules |
| [`docs/PRD.md`](docs/PRD.md) | Scope, requirements, success criteria, limitations |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Graph, state, API contract |
| [`docs/DESIGN.md`](docs/DESIGN.md) | UI/UX spec, accessibility, bilingual copy |
| [`docs/TASKS.md`](docs/TASKS.md) | Ordered build tasks |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Deploying to the DLSU ALTDSI VM |
| [`qa/TEST-PLAN.md`](qa/TEST-PLAN.md) | Test strategy and coverage map |

**If you change something a doc describes, update the doc in the same commit.** The map of what-changes-what is in `CLAUDE.md`.

---

## Troubleshooting

**`uv sync` fails on torch.** Check `python --version`. We build against 3.13–3.14; torch has no wheels below that range here.

**Backend takes ~13s to start.** Expected. The embedding model loads once at boot.

**Embedding model re-downloads every run.** Your `~/.cache/huggingface` is not persisting. Check permissions.

**Frontend shows a network error.** The backend is not on :8000. Vite proxies `/api` there.

**Cypress specs fail with "element not found".** Expected until the UI is built — the specs encode the `DESIGN.md` contract and are the acceptance criteria for tasks T5 and T14. See `qa/TEST-PLAN.md § Known gaps`.

**400 mentioning `temperature` or `top_p`.** Something passed a sampling parameter. We pass none — providers disagree about which they accept, so any of them breaks the `LLM_MODEL` switch. Only `backend/app/llm.py` should construct the model.

**429 / rate limited.** `llm.py` backs off and retries; raise `LLM_RETRY_BACKOFF` if an eval run keeps tripping it.

**Auth error on the first analysis.** You have no `backend/.env`, or its `AWS_BEARER_TOKEN_BEDROCK` is blank. It is gitignored by design, so pulling the repo never gives you one — `cp .env.example .env` and paste the sandbox token in. A quick check: `uv run python check_bedrock_connection.py`.

**You committed a key by accident.** Rotate it immediately; do not just delete the line. It is in the history and remains readable to anyone who clones.

---

## Team

Aki (Lead, QA) · Allen (Tech) · Nian (Domain / knowledge base) · James (UX) · Lui (Scribe)

Mentor: Rozelle Samonte, Accenture.

## Attribution

Message corpus: [scottleechua/data](https://github.com/scottleechua/data) — PH spam and marketing SMS, CC BY 4.0. Advisory content is quoted verbatim from BSP, NPC, DICT, PNP-ACG, and bank/e-wallet fraud pages; see `knowledge-base/ATTRIBUTION.md`.
