# Elderly Scam Shield

Paste a suspicious SMS, email, or URL and get a verdict, a plain-language explanation of the red flags, and concrete next steps — in Filipino/Taglish or English.

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
cp .env.example .env     # add your provider key
uv run uvicorn app.main:app --reload --port 8000
```

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

`backend/.env`:

| Variable | Default | |
|---|---|---|
| `SHIELD_MODEL` | `anthropic:claude-opus-5` | Any `init_chat_model` string — `anthropic:`, `google_genai:`, `bedrock_converse:` |
| `SHIELD_MAX_TOKENS` | `4096` | Bounds thinking plus response together on Claude 5 |
| `SHIELD_CONFIDENCE_THRESHOLD` | `0.70` | Set from the eval sweep, not asserted |
| `SHIELD_KB_PATH` | fixture | Point at `knowledge-base/out/kb.sqlite` once it lands |

Plus whichever provider key matches `SHIELD_MODEL` — `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or AWS credentials.

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
| [`qa/TEST-PLAN.md`](qa/TEST-PLAN.md) | Test strategy and coverage map |

**If you change something a doc describes, update the doc in the same commit.** The map of what-changes-what is in `CLAUDE.md`.

---

## Troubleshooting

**`uv sync` fails on torch.** Check `python --version`. We build against 3.13–3.14; torch has no wheels below that range here.

**Backend takes ~13s to start.** Expected. The embedding model loads once at boot.

**Embedding model re-downloads every run.** Your `~/.cache/huggingface` is not persisting. Check permissions.

**Frontend shows a network error.** The backend is not on :8000. Vite proxies `/api` there.

**Cypress specs fail with "element not found".** Expected until the UI is built — the specs encode the `DESIGN.md` contract and are the acceptance criteria for tasks T5 and T14. See `qa/TEST-PLAN.md § Known gaps`.

**400 from Anthropic mentioning `temperature`.** Something passed a sampling parameter. `temperature`, `top_p`, `top_k`, and `budget_tokens` are all rejected on Claude 5 models. Only `backend/app/llm.py` should construct the model.

---

## Team

Aki (Lead, QA) · Allen (Tech) · Nian (Domain / knowledge base) · James (UX) · Lui (Scribe)

Mentor: Rozelle Samonte, Accenture.

## Attribution

Message corpus: [scottleechua/data](https://github.com/scottleechua/data) — PH spam and marketing SMS, CC BY 4.0. Advisory content is quoted verbatim from BSP, NPC, DICT, PNP-ACG, and bank/e-wallet fraud pages; see `knowledge-base/ATTRIBUTION.md`.
