# Architecture — Kalasag

Companion to `PRD.md`. Implements the mentor-confirmed shape from the 2026-07-29 consultation: three LLM agents behind a deterministic Python front end, with the guardrail inside the Detector rather than as its own node.

## Overview

```
frontend (Vite / React / TS / Tailwind)
   │  POST /api/analyze  { text, language }
   ▼
backend (FastAPI)
   │
   ├─ preprocess.py ──── Python only ──── detect type · redact PII
   │                                      raw text stops here
   ▼
LangGraph  GraphState
   │
   ├─ retrieve ── LLM: Taglish → EN red-flag concepts
   │              └─► vector search over kb_chunks (local embeddings)
   │
   ├─ detect ──── LLM: verdict + confidence + red flags, guardrail rules in prompt
   │                 │
   │                 └─ confidence < threshold AND reflections == 0
   │                       └─► reflect ──► detect   (bounded at one pass)
   │
   └─ advise ──── LLM: EN|TL explanation + next steps
                  hotlines injected as DATA from keyed lookup
   ▼
   Verdict → Explanation → Next steps → Contacts → Similar scams
```

## Why this shape

| Decision | Reason |
|---|---|
| Preprocessing is Python, not an LLM | Message-type detection is a `startswith("http")`-class check. Redaction must be deterministic — a model that occasionally forgets to redact an OTP is worse than no redaction. |
| Retrieval is its own agent | Mentor ruling 4. The LLM step earns its cost by rewriting Taglish into English red-flag concepts, which is also the cheapest mitigation for cross-lingual retrieval. |
| RAG rather than pattern matching | Mentor ruling 3. Regex breaks the moment scammers write a new script; vector search matches on intent and can surface "this pattern may be relevant" for messages never seen before. |
| Guardrail lives in the Detector | Mentor ruling 7. A separate guardrail node is either a third LLM round-trip or a redundant Python pass over work the Detector already did. |
| Retry is self-reflection, not re-run | Mentor ruling 6. Re-running from step one produces the same output. The second pass carries the failure reason and asks whether the judgment stands. |
| Advisor stays separate from the Detector | Register control and hotline selection are a different prompt job from detection. Merging produces one over-stuffed prompt, which the mentor flagged as a hallucination cause in both directions. |
| Embeddings are local and provider-independent | If embeddings came from the chat provider, switching providers would force a full KB re-embed. Decoupling also means no network call on the retrieval hot path. |

The cycle is the honest justification for LangGraph over a plain chain — chains cannot express cycles.

## Repository layout

```
CLAUDE.md  README.md  .gitignore
docs/               PRD.md · ARCHITECTURE.md · DESIGN.md · TASKS.md + consultation notes
backend/
  pyproject.toml
  app/
    main.py           FastAPI: POST /api/analyze, GET /api/health, GET /api/meta
                      + mounts static/ as the frontend when deployed
    static/           built frontend, deploy only — gitignored, absent in dev
    config.py         settings from env
    llm.py            the provider switch — the only module importing a provider SDK
    schemas.py        pydantic request/response models
    preprocess.py     type detection + PII redaction (pure, no LLM)
    graph/
      state.py        GraphState
      build.py        StateGraph wiring + conditional edge
      nodes/retrieve.py  nodes/detect.py  nodes/advise.py
    retrieval/
      embedder.py     local sentence-transformer, cached
      store.py        kb_chunks vector search over SQLite
      contacts.py     keyed lookup: brand_rebuttals, reporting_contacts
    prompts/          retrieve.md · detect.md · reflect.md · advise.md
  tests/
    fixtures/kb_fixture.sqlite  + make_fixture.py
    test_config.py test_llm.py test_preprocess.py
    test_retrieval.py test_graph.py test_api.py
  eval/
    run_eval.py       55-message eval + threshold sweep
    results/
frontend/
  vite.config.ts      vite + tailwind + vitest config in one file
  src/
    App.tsx  api.ts  i18n.ts  test-setup.ts
    components/       InputPanel · VerdictCard · RedFlagList · NextSteps
                      ContactList · SimilarScams · LanguageToggle
                      + colocated *.test.tsx per component
qa/                   QA workspace — own package.json, own node_modules
  cypress.config.ts
  TEST-PLAN.md
  cypress/
    e2e/
      analyse/        verdict-scam · verdict-variants · red-flags · next-steps
      language/       toggle
      privacy/        redaction
      errors/         error-states
      a11y/           accessibility
      smoke/          live-pipeline   ← the only spec hitting a real LLM
    fixtures/         meta.json + one per verdict
    support/          e2e.ts · commands.ts
knowledge-base/       Nian's subtree — read-only to us
eval-set-candidate-55.csv
```

`app/graph/` holds control flow, `app/retrieval/` holds data access, `app/prompts/` holds product logic. A node function should be readable end to end without opening another file.

## Graph state

```python
class GraphState(TypedDict):
    redacted_text: str
    message_type: Literal["sms", "email", "url"]
    redactions: list[str]              # labels only, e.g. ["OTP", "PHONE"] — never values
    output_language: Literal["en", "tl"]

    concepts_en: list[str]             # retrieve
    retrieved: list[Chunk]             # retrieve

    verdict: Verdict                   # detect
    confidence: float                  # detect
    first_verdict: Verdict             # detect, first pass only
    first_confidence: float            # detect, first pass only
    red_flags: list[RedFlag]           # detect
    reflection_count: int              # detect
    low_confidence_reason: str | None  # detect → reflect

    advice: Advice                     # advise
```

**Not in state:** the raw unredacted input. This is a privacy requirement from the PRD, enforced by never putting it there rather than by remembering to strip it later.

`redactions` carries labels, not values, so the UI can say "we removed an OTP before analysing" without the OTP existing anywhere downstream.

## Nodes

### `preprocess` — Python

Detects message type: a bare URL, an email (has headers or a subject line), otherwise SMS.

Redacts in this order, each replaced by its label:

| Pattern | Label |
|---|---|
| 4–8 digits near `otp`, `code`, `pin`, `verification` | `[OTP]` |
| 13–19 digit runs (card numbers) | `[CARD]` |
| PH mobile formats: `09xxxxxxxxx`, `+639xxxxxxxxx` | `[PHONE]` |
| 10–16 digit runs (account numbers) | `[ACCOUNT]` |
| Email addresses | `[EMAIL]` |

`PHONE` runs before `ACCOUNT` because a PH mobile number is itself an 11-digit run — the generic account pattern firing first would mislabel every phone number as an account. More specific patterns fire first throughout.

URLs are **not** redacted — the domain is the primary signal the Detector needs.

### `retrieve` — LLM + vector search

The LLM receives the redacted message and returns 3–6 English red-flag concepts (`"claims account suspended"`, `"urgency deadline"`, `"shortened link"`). Those concepts, plus the raw redacted text, are embedded and matched against `kb_chunks` by cosine similarity. Top-k defaults to 6.

This closes open question 3 from the proposal: the Taglish→English hop happens before retrieval, so a Taglish query reaches an English corpus through concepts rather than through embedding luck.

Retrieval filters `retrievable = 1`, which excludes both `LEGIT` examples and every eval-set holdout.

### `detect` — LLM

Returns structured JSON: verdict, confidence 0–1, red flags each citing a `chunk_id`, and a one-line reason when confidence is low.

Guardrail rules live in `prompts/detect.md`, framed as rules to follow strictly:

- Never claim certainty. There is no `SAFE` verdict.
- Cite a retrieved chunk for every red flag, or say the KB had nothing matching.
- Never instruct the user to click, reply, or call a number from the message.
- When genuinely unsure, emit `UNCLEAR` and recommend asking a trusted family member.

Conditional edge after `detect`:

```python
def route(state):
    if state["confidence"] >= THRESHOLD:  return "advise"
    if state["reflection_count"] >= 1:    return "advise"
    return "reflect"
```

The second clause is what makes the loop terminate. `reflect` is not a separate LLM call — it rewrites the Detector's prompt with the prior verdict, its confidence, and `low_confidence_reason`, then re-enters `detect`. Worst case is four LLM calls per request.

`THRESHOLD` is set from the eval sweep, not hardcoded at 70%.

### `advise` — LLM

Receives the verdict, red flags, retrieved chunks, and — as structured data, not prose — the brand rebuttal and reporting contacts fetched by key. Produces the explanation and next steps in the selected language.

`prompts/advise.md` specifies register explicitly. Target: plain Filipino/Taglish as spoken. Avoid *panganib*, *pagpapatunay*, *pagpapatibay*; prefer *delikado*, *i-verify*, *tiyakin*. Do not translate brand names, hotline numbers, or app names.

Contacts are passed through verbatim and the prompt states they must be reproduced exactly. This is why `contacts.py` exists as a separate module from `store.py` — the type system keeps semantic search away from phone numbers.

## Provider abstraction

`llm.py` is the only module importing a provider SDK.

```python
from langchain.chat_models import init_chat_model

from app.config import get_settings

def get_model() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(settings.model_id, max_tokens=settings.max_tokens)

def invoke_with_retry(runnable: Runnable, payload: Any) -> Any:
    ...  # 429 backoff; build the chain first, wrap last
```

Settings are reached through `get_settings()` rather than a module-level `settings` object. The `lru_cache` on it means one read per process, and `cache_clear()` lets a test set an env var and see the change — a module-level instance would freeze whatever env existed at first import.

`LLM_MODEL` accepts any `init_chat_model` string. The default is `bedrock_converse:global.anthropic.claude-sonnet-5` — the Accenture sandbox, verified live end to end on 2026-08-06 (T13 spot check: three messages, all verdicts correct, reflection fired and terminated). The `global.` prefix is required: ap-southeast-1 serves Claude Sonnet 5 only through the global inference profile, and the bare model ID fails from Singapore. Auth is a bearer token in `AWS_BEARER_TOKEN_BEDROCK`; the `_BEDROCK` suffix is what botocore looks for, and without it auth silently falls back to SigV4 and fails.

**Gemini support was removed on 2026-08-06.** The project started on the Gemini free tier because the sandbox model list was unconfirmed (then open question 2). Once the sandbox was verified, the free-tier key was deleted and `langchain-google-genai` dropped — one working provider beats two half-maintained ones, and the switch itself keeps working: re-adding any provider is an `uv add` of its langchain package plus an `LLM_MODEL` string. Two Gemini findings worth keeping: the free tier granted zero quota on `gemini-2.5-pro` (T1: `429 RESOURCE_EXHAUSTED`, `limit: 0` — not a rate limit that waiting clears), and Flash/Flash-Lite both worked and were verified live before the move.

**The project pays for no LLM API.** The sandbox serves Claude models (`anthropic.claude-*`) on AWS billing — not a key we buy.

**Never pass sampling parameters** — no `temperature`, `top_p`, or `top_k`. This is a portability rule rather than a per-model quirk: providers disagree about which are accepted, and some reject them outright, so a parameter that works under one `LLM_MODEL` and fails under another defeats the switch. Passing none works everywhere. Behaviour is steered by the prompt.

**`max_tokens` may bound reasoning tokens as well as visible output** on models that reason before answering. Leave headroom or responses truncate mid-answer.

`llm.py` also owns **retry with backoff on HTTP 429**. A full eval run is roughly 200 calls and the sandbox's rate limits are undocumented, so the eval harness depends on this rather than implementing its own.

Retry is exposed as `invoke_with_retry(runnable, payload)` rather than folded into `get_model()`. LangChain's `Runnable.with_retry()` returns a plain `Runnable`, which no longer offers `with_structured_output()` — the Detector needs that, so retry has to be applied *after* the chain is built, not to the bare model. It also only accepts exception *types*, and each provider raises its own for a 429; `is_rate_limit()` matches on the wire status and wording instead, so nothing here imports a provider's exception classes. Backoff escalates as `LLM_RETRY_BACKOFF × attempt` over `MAX_ATTEMPTS = 4`. Non-429 failures raise immediately — retrying a malformed prompt just burns two minutes and the same quota.

Two refinements are deliberately **not** implemented. The loop ignores the provider's own retry-delay hint, and it cannot tell a per-minute 429 from an exhausted quota, so a hard quota exhaustion burns all four attempts before raising. Both cost only wall-clock time, and both were observed only on Gemini's free tier before its removal; the eval runs on the Bedrock sandbox, where quota is expected to be the non-issue. If the sandbox turns out to be tightly limited, revisit before the T17 live run — a 200-call eval is where the wasted minutes would add up.

`config.py` calls `load_dotenv(.env, override=False)` at import. pydantic-settings reads the configured values into `Settings` but does not put anything in `os.environ`, and the provider SDKs read their credentials (`AWS_*`) from there — without this, a `.env` with a valid token still fails to authenticate. `override=False` keeps an already-exported variable winning over the file.

## Retrieval

`embedder.py` loads `intfloat/multilingual-e5-small` (384-dim) once and caches it. ~120MB, downloaded on first run. No network on the hot path afterwards, so the demo survives a flaky venue connection for everything except the LLM call itself.

`store.py` reads `knowledge-base/out/kb.sqlite`, falling back to `backend/tests/fixtures/kb_fixture.sqlite` when the real KB is absent. Cosine similarity is computed in Python over the loaded vectors — the KB is under 2,000 rows, so an index is unnecessary complexity.

Schema consumed (Nian's, unchanged): `kb_chunks`, `brand_rebuttals`, `reporting_contacts`, `lure_patterns`, `message_examples`, `advisories`, `sources`.

The `embedding` column ships unpopulated. We populate it with our local model on first build — this is the one change to KB *data* we make, and it happens in `backend`, writing to a copy, never to Nian's source tree.

## API

### `POST /api/analyze`

```json
{ "text": "BDO ALERT: Your account is on hold...", "language": "tl" }
```

```json
{
  "verdict": "SCAM",
  "confidence": 0.91,
  "reflected": false,
  "message_type": "sms",
  "redactions": ["OTP"],
  "redacted_text": "BDO ALERT: Your account is on hold...",
  "red_flags": [
    { "label": "Claims your account is on hold",
      "detail": "Real suspensions appear when you log in, not as a text with a link.",
      "chunk_id": "lure-account-suspended" }
  ],
  "explanation": "Scam po ito...",
  "next_steps": ["Huwag i-click ang link.", "Tawagan ang BDO sa opisyal nilang hotline."],
  "contacts": [
    { "organisation": "BDO Unibank", "hotline": "(02) 8631-8000", "url": "https://www.bdo.com.ph/" },
    { "organisation": "I-ARC", "hotline": "1326", "url": "https://www.cybersecurity.ph/cybercrime-reporting/" }
  ],
  "similar_scams": [{ "text": "...", "scam_type": "bank-impersonation" }],
  "kb_freshness": "2026-08-06",
  "model_id": "bedrock_converse:global.anthropic.claude-sonnet-5"
}
```

`GET /api/health` → liveness. `GET /api/meta` → `kb_freshness`, `model_id`, chunk count. The frontend calls `/api/meta` once at load for the freshness badge.

Errors return `{ "error": { "code": "...", "message": "..." } }` with a user-safe message. **Provider errors never echo the request body**, which would leak the input we spent preprocessing to protect.

## Serving

The frontend calls **relative** paths (`/api/analyze`, `/api/meta`). It never holds a base URL, in dev or in production. Two consequences, both deliberate:

- **In dev**, vite proxies `/api` to `localhost:8000` (`vite.config.ts`). Same origin, so there is no CORS to configure.
- **In deployment**, `main.py` mounts the built frontend from `backend/static/` at `/`, so one uvicorn process serves the app and the API on one port. Again same origin.

The mount is registered last in `main.py` because FastAPI matches routes in registration order — a mount at `/` declared earlier would swallow `/api/*`. It is guarded by `FRONTEND_DIST.is_dir()`, since `StaticFiles` raises at construction when the directory is missing; `backend/static/` is gitignored and absent in dev and CI, so the mount is inert everywhere but a deployed box.

`POST /api/analyze` is declared `def`, not `async def`, and that is load-bearing. `graph.invoke()` is synchronous and holds for the full 40-second analysis; under `async def` it blocks the event loop, so concurrent callers serialise — measured against the deployed VM, two simultaneous requests returned in 22s and 59s, the second having waited out the first. FastAPI runs a plain `def` endpoint in a threadpool instead, so requests overlap. `health` and `meta` stay `async` because neither blocks meaningfully.

Single-origin was chosen over hosting the frontend separately (Vercel was the alternative considered) because a static host serves HTTPS while the deployment target serves plain HTTP on a non-standard port, and browsers block mixed-content `fetch` unconditionally. Fixing that needs a certificate for a domain we do not control. Splitting the origins would also add a CORS allowlist and an API base URL config — work spent to make the app strictly worse. Full procedure in `docs/DEPLOYMENT.md`.

## Testing

Three layers. Full strategy and coverage map in `qa/TEST-PLAN.md`.

### Backend — pytest, `backend/tests/`

| File | Covers |
|---|---|
| `test_config.py` | Every settings var is read; defaults hold when unset; unrelated env vars are ignored. |
| `test_llm.py` | `get_model()` passes `max_tokens` and no sampling parameter; 429 detection across provider wordings; retry escalates, stops at `MAX_ATTEMPTS`, and does not fire on non-429s. |
| `test_preprocess.py` | Each redaction pattern; OTP survives as a label; URLs are preserved; type detection for all three types. |
| `test_retrieval.py` | Against the fixture KB: a Taglish query retrieves an English advisory; `LEGIT` rows never appear; eval-set text never appears. |
| `test_graph.py` | With `FakeListChatModel`: low confidence reflects exactly once; high confidence goes straight to `advise`; a second low-confidence pass still terminates. |
| `test_api.py` | `TestClient` on `/api/analyze` — response shape, both languages, malformed input. |

Graph tests use a fake model so control flow is tested without network, cost, or nondeterminism. This is the test that matters most: the reflection loop is the only place the system can hang.

### Frontend — Vitest, colocated

Component tests sit next to their components as `*.test.tsx`. Vitest reads the same `vite.config.ts` the app builds with, so there is no second transform pipeline to keep in sync.

### E2E — Cypress, `qa/`

One spec file per feature, grouped by feature folder. Every spec except `smoke/` stubs `/api/analyze` and `/api/meta` with fixtures via `cy.intercept`, which makes the suite fast, free, and deterministic while still covering all four verdicts and every error state in `DESIGN.md`.

`smoke/live-pipeline.cy.ts` is the exception: it runs the real backend against a real LLM and asserts the response contract from the API section above. It is excluded from `npm run cy:run` and invoked deliberately with `npm run e2e:smoke`.

**Why the split.** Stubs cannot detect the frontend and backend disagreeing about the response shape — that is exactly what the smoke spec is for. Conversely, running the whole suite live would cost money per run, take ~20s per spec, and fail on provider rate limits, which means it would stop being run. Each layer covers the other's blind spot.

The default Cypress viewport is 390×844 because the elderly user is on a phone; the desktop caregiver case is asserted explicitly where it matters.

## Evaluation

`eval/run_eval.py` runs all 55 gold-labelled messages through the full pipeline with the reflection threshold forced to 0.95, so nearly every message produces both a first and a second pass. That is what makes the sweep computable from a single run: verdict(t) = second-pass verdict where first-pass confidence < t, else first-pass verdict — `first_verdict`/`first_confidence` in graph state exist for this. Gold labels are binary; SCAM and LIKELY_SCAM count as SCAM, and UNCLEAR counts against the scam class — the conservative mapping, since an UNCLEAR on a real scam is a miss the user pays for. It emits:

- Confusion matrix against `gold_label`.
- Accuracy, precision, recall, F1.
- A threshold sweep from 0.50 to 0.95 in 0.05 steps, showing how many messages would reflect and what accuracy results.
- A per-message table with verdict, confidence, and whether reflection fired.

Output is markdown, written to `eval/results/`, and pasted into the deck.

Running it twice under different `LLM_MODEL` values is the model bake-off. That answers "how did you choose your model" with measurements instead of a spec-sheet comparison, and it satisfies the mentor's framing that the binding constraint is access, not capability.

**Honest framing for the deck:** the threshold is calibrated on the same 55 messages we report accuracy on. That is fitting to the test set. We say so rather than presenting it as held-out accuracy.

## Risks

| Risk | Mitigation |
|---|---|
| Nian's KB does not arrive | Fixture KB built from his documented schema; demo runs on a smaller corpus and we say so. |
| Sentence-transformer download fails at the venue | Pull it on day one, commit the cache path to the runbook. |
| No internet at the presentation | Record a screen capture as backup. Everything except the LLM call is already local. |
| Reflection loop cost | Bounded at one pass; worst case four LLM calls. |
| Provider access lost mid-week | `LLM_MODEL` swap, no code change. |
| Register drifts to formal Tagalog | Explicit register rules in `advise.md`; native-speaker review is criterion S6. |
