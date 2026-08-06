# Elderly Scam Shield

Paste a suspicious SMS, email, or URL and get a verdict, a plain-language explanation of the red flags, and concrete next steps — in Filipino/Taglish or English.

STSP001 capstone, AY2526-T3. A LangGraph pipeline over a curated Philippine scam knowledge base.

```
paste → preprocess (redact PII) → retrieve → detect ⇄ reflect → advise → verdict
```

## Docs

| File | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Conventions, ownership, pipeline invariants — read first |
| [`docs/PRD.md`](docs/PRD.md) | Scope, requirements, success criteria |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Graph, state, API contract |
| [`docs/DESIGN.md`](docs/DESIGN.md) | UI/UX spec, accessibility, bilingual copy |
| [`docs/TASKS.md`](docs/TASKS.md) | Ordered build tasks |

## Setup

Requires Python 3.14 with [`uv`](https://docs.astral.sh/uv/), and Node 20+.

```bash
# backend
cd backend
uv sync
cp .env.example .env        # set SHIELD_MODEL and your provider key
uv run uvicorn app.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

First backend run downloads the embedding model (~120MB). Do this before you need it.

## Configuration

| Variable | Default | |
|---|---|---|
| `SHIELD_MODEL` | `anthropic:claude-opus-5` | Any `init_chat_model` string — `anthropic:`, `google_genai:`, `bedrock_converse:` |
| `SHIELD_MAX_TOKENS` | `4096` | Bounds thinking plus response together on Claude 5 |
| `SHIELD_CONFIDENCE_THRESHOLD` | `0.70` | Set from the eval sweep, not asserted |
| `SHIELD_KB_PATH` | fixture | Point at `knowledge-base/out/kb.sqlite` once it lands |

Switching providers requires no code change and no re-embedding — embeddings are local and provider-independent.

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm test
```

## Evaluation

```bash
cd backend && uv run python eval/run_eval.py
```

Runs all 55 gold-labelled messages through the full pipeline and writes a confusion matrix, accuracy/precision/recall/F1, and a confidence-threshold sweep to `eval/results/`.

## Team

Aki (Lead) · Allen (Tech) · Nian (Domain / knowledge base) · James (UX) · Lui (Scribe)

Mentor: Rozelle Samonte, Accenture.

## Attribution

Message corpus: [scottleechua/data](https://github.com/scottleechua/data) — PH spam and marketing SMS, CC BY 4.0. Advisory content is quoted verbatim from BSP, NPC, DICT, PNP-ACG, and bank/e-wallet fraud pages; see `knowledge-base/ATTRIBUTION.md`.
