# Kalasag — the whole thing, explained

One document that answers "what is this and how does it work" end to end: the product,
the flow, the architecture, each layer, LangGraph, RAG, and how to deploy and redeploy it.

It is a **companion**, not a replacement. Where a topic has an owning doc, this file gives
you the working understanding and points at the authority:

| Topic | Authority |
|---|---|
| Scope, requirements, success criteria, limitations | `docs/PRD.md` |
| Graph shape, state, API contract, module boundaries | `docs/ARCHITECTURE.md` |
| Screens, accessibility rules, EN/TL copy | `docs/DESIGN.md` |
| Ordered build tasks | `docs/TASKS.md` |
| Test strategy and coverage map | `qa/TEST-PLAN.md` |
| Deployment runbook | `docs/DEPLOYMENT.md` |
| Conventions, ownership, invariants | `CLAUDE.md` |
| Knowledge base build | `knowledge-base/README.md` |

If this guide and one of those disagree, the owning doc wins and this file is stale — fix it.

---

## 1. What the app is

An elderly Filipino, or the family member screening messages for them, pastes a suspicious
SMS, email body, or URL into one box. Kalasag returns:

**verdict → explanation → next steps**

in plain Filipino/Taglish or English, grounded in a curated Philippine scam knowledge base.

STSP001 capstone, AY2526-T3. Renamed from "Elderly Scam Shield" to **Kalasag** on
2026-08-06 — the hardwood shield carried by pre-colonial Filipino warriors, and the shield
on the PNP seal, which is the agency the app routes reports to.

### Who it is for

- **Primary: the elderly recipient.** Low tech confidence, small screen, possibly reduced
  vision, and panicking because urgency framing is exactly what the scam exploits.
- **Secondary: the family caregiver.** Comfortable in English, screening remotely, wants
  enough detail to explain the verdict to the person who got the message.

The `English | Tagalog` toggle exists because those two people want different output
languages out of the same analysis.

### The four verdicts

| Verdict | Headline (EN) | Headline (TL) |
|---|---|---|
| `SCAM` | THIS IS A SCAM | SCAM ITO |
| `LIKELY_SCAM` | LIKELY A SCAM | MALAMANG SCAM ITO |
| `UNCLEAR` | NOT SURE | HINDI SIGURADO |
| `LIKELY_LEGIT` | LOOKS LEGITIMATE | MUKHANG LEHITIMO |

**There is no `SAFE` verdict, and that is deliberate.** The system cannot verify a sender,
so `LIKELY_LEGIT` is the ceiling and it still renders "verify independently before acting."
This is pipeline invariant 3 — breaking it is a correctness bug, not a copy change.

### What it does not do

Out of scope this term: screenshot/OCR input, voice input and TTS, telco integration, live
threat feeds, languages beyond Filipino/English/Taglish, accounts, and any persistence of
what the user submitted. The PRD lists these under **Out this term** with the reasoning.

---

## 2. The flow of the app

### What the user sees

1. **Idle.** Header with the shield mark, the `English | Tagalog` toggle, a tagline, one
   textarea, one big button, a privacy line ("We don't save your message."), and a KB
   freshness date pulled from `/api/meta` at page load.
2. **Analysing.** A four-step progress display — reading the message, looking for similar
   scams, checking the red flags, preparing the advice. This is cosmetic pacing, not
   real progress events; the analysis takes ~40s and a spinner alone reads as broken.
3. **Result.** Verdict card, explanation paragraph, red-flag list, next steps with
   contacts, similar scams, the analysed (redacted) message, a standing uncertainty note,
   and a "check another message" reset.
4. **Error.** One user-safe message and a retry button. Provider errors never surface
   their text.

The language toggle switches all UI chrome instantly from `i18n.ts`. It does **not** re-run
the analysis — the model-authored `explanation` and `next_steps` stay in whatever language
was selected at submit time. That is requirement F8 read literally: the toggle is free, and
re-analysing on a toggle would cost another 40s and another four LLM calls.

### What happens per request

```
user pastes text
   │
   ▼
POST /api/analyze  { text, language }
   │
   ├─ preprocess.py ── pure Python ── detect type · redact PII
   │                   ⚠ raw text stops here. It never enters graph state and is never logged.
   ▼
LangGraph, on GraphState
   │
   ├─ retrieve ── LLM: Taglish/English → 3-6 English red-flag concepts
   │              └─► embed concepts + redacted text → cosine search over kb_chunks → top 6
   │
   ├─ detect ──── LLM: verdict + confidence + red flags (each citing a chunk_id)
   │                 │   guardrail rules live in the prompt
   │                 └─ confidence < CONFIDENCE_THRESHOLD  AND  reflection_count == 0
   │                       └─► reflect ──► detect     (bounded at exactly one extra pass)
   │
   └─ advise ──── LLM: explanation + next steps in the chosen language
                  hotlines injected as DATA from a keyed lookup, never generated
   ▼
AnalyzeResponse → verdict · explanation · next steps · contacts · similar scams
```

**Cost per request:** 3 LLM calls normally, 4 when reflection fires. Measured on the
deployed VM: 40.6s without reflection, 44.0s with. The reflection pass costs only ~3.5s
because the second `detect` call is shorter, not because it is cheap — it is a real call.

---

## 3. Architecture

### The shape and why

| Decision | Reason |
|---|---|
| Preprocessing is Python, not an LLM | Type detection is a `startswith("http")`-class check. Redaction must be deterministic — a model that occasionally forgets to redact an OTP is worse than no redaction at all. |
| Retrieval is its own agent | Mentor ruling 4. The LLM step earns its cost by rewriting Taglish into English red-flag concepts, which is also the cheapest fix for cross-lingual retrieval. |
| RAG rather than regex | Mentor ruling 3. Pattern matching breaks the moment scammers write a new script; vector search matches on intent. |
| Guardrail inside the Detector | Mentor ruling 7. A separate guardrail node is either a third round-trip or a redundant Python pass over work the Detector already did. |
| Retry is self-reflection, not a re-run | Mentor ruling 6. Re-running from step one produces the same output. The second pass carries the failure reason and asks whether the judgment stands. |
| Advisor separate from Detector | Register control and hotline selection are a different prompt job from detection. Merging gives one over-stuffed prompt, which the mentor flagged as a hallucination cause in both directions. |
| Embeddings local, not from the chat provider | Otherwise switching `LLM_MODEL` forces a full KB re-embed. Also means no network call on the retrieval hot path. |

**The cycle is the honest justification for LangGraph over a plain chain.** Chains cannot
express cycles. If you are asked at the panel why not LangChain alone, that is the answer.

### Repository layout

```
CLAUDE.md  README.md  eval-set-candidate-55.csv
docs/                PRD · ARCHITECTURE · DESIGN · TASKS · DEPLOYMENT · GUIDE (this file)
backend/             FastAPI + LangGraph, pytest              Aki, Allen
  app/
    main.py            the three routes + the static mount
    config.py          every env var, read here and nowhere else
    llm.py             the provider switch — only module importing a provider SDK
    schemas.py         pydantic request/response models
    preprocess.py      type detection + PII redaction (pure, no LLM, no I/O)
    graph/             state.py · build.py · nodes/{retrieve,detect,advise,common}.py
    retrieval/         embedder.py · store.py · contacts.py
    prompts/           retrieve.md · detect.md · reflect.md · advise.md
  tests/               7 pytest modules + fixtures/kb_fixture.sqlite
  eval/run_eval.py     55-message eval + threshold sweep
  static/              built frontend — deploy only, gitignored, absent in dev
  var/kb_embedded.sqlite   backend-owned embedded copy of the KB
frontend/            Vite + React 19 + TS + Tailwind v4, Vitest   James
qa/                  Cypress E2E, own package.json                Aki
knowledge-base/      Nian's subtree — read-only to us             Nian
```

`app/graph/` holds control flow, `app/retrieval/` holds data access, `app/prompts/` holds
product logic. A node function should read end to end without opening another file.

### Directory ownership

| Path | Owner |
|---|---|
| `backend/` | Aki (Lead), Allen (Tech) |
| `frontend/` | James (UX) |
| `qa/` | Aki (QA) |
| `knowledge-base/` | Nian (Domain) — **incoming subtree, do not author here** |
| `docs/` | Lui (Scribe) |

Branches are `<type>/<what-changed>` — `feat/provider-switch`, `fix/redaction-otp`. No
owner names, no task numbers: the branch says what changed, and `git log` already says who.

---

## 4. How the frontend works

**Stack:** Vite 8, React 19, TypeScript, Tailwind v4, Vitest for component tests.

### State machine

`App.tsx` is the whole application state — four phases and nothing more:

```ts
type Phase = 'idle' | 'analysing' | 'result' | 'error'
```

No router, no state library, no context. There is one screen. Anything heavier would be
speculative structure for a single-view app.

Language is a `useState<Language>` seeded from `localStorage['kalasag-lang']`, defaulting
to **`tl`** — the primary user is the elderly Filipino, so Tagalog is the default and
English is the opt-in. It also writes `document.documentElement.lang` on change, which is
what screen readers read to pick a voice.

### Components

| Component | Job |
|---|---|
| `InputPanel` | Textarea, submit button, privacy line, freshness badge, length warning |
| `AnalysingState` | The four-step progress display |
| `VerdictCard` | Headline + subtitle, colour-coded per verdict |
| `RedFlagList` | One row per red flag: label + detail |
| `NextSteps` | Ordered actions plus the contact list |
| `ContactList` | Organisation, hotline, official URL |
| `SimilarScams` | Up to 3 corpus messages of the same shape |
| `AnalysedMessage` | The redacted text plus "we removed these before analysing" |
| `ErrorState` | One safe message + retry |
| `LanguageToggle` | EN/TL switch |

Four of these have colocated `*.test.tsx` files. Tests live next to the component
deliberately — tests in a distant folder stop being updated when their source changes.

### i18n

`src/i18n.ts` holds **every** user-facing string in both languages as one flat key map,
with `t(lang, key, vars)` for lookup. The `Copy` type is derived from the English object,
so a missing Tagalog key is a TypeScript error rather than a blank label at the demo.

`REDACTION_LABELS` maps the backend's redaction labels (`OTP`, `CARD`, `ACCOUNT`, `PHONE`,
`EMAIL`) into readable phrases per language, so the UI can say "we removed a one-time
password (OTP)" without the OTP itself existing anywhere on the client.

The Tagalog copy is plain Taglish as spoken, not textbook Tagalog: *i-click*, *i-block*,
*account*, *link*, *i-verify* stay in English because that is what people actually say, and
`po` appears in direct address because that is how you speak to an elder.

### Talking to the API

`src/api.ts` is two functions, `analyze()` and `fetchMeta()`, and both call **relative**
paths — `/api/analyze`, `/api/meta`. The frontend never holds a base URL, in dev or in
production. That single choice is what makes deployment simple:

- **In dev**, `vite.config.ts` proxies `/api` → `http://localhost:8000`. Same origin, so
  there is no CORS to configure.
- **In deployment**, FastAPI serves the built frontend itself, so `/` and `/api/*` are
  literally the same origin on the same port.

### Running it

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 — run the backend on :8000 too
npm run build      # → frontend/dist/
npm test           # Vitest, component tests
npm run lint       # oxlint
```

---

## 5. How the backend works

**Stack:** Python 3.13–3.14, `uv`, FastAPI, LangGraph, LangChain, SQLite, numpy,
sentence-transformers. Always `uv`, never `pip install`.

### The three routes

| Route | Shape |
|---|---|
| `GET /api/health` | `{"status": "ok"}` — liveness, touches nothing |
| `GET /api/meta` | `{ kb_freshness, model_id, chunk_count }` — called once at page load |
| `POST /api/analyze` | The pipeline. Request `{ text, language }`, response below |

```json
{
  "verdict": "SCAM",
  "confidence": 0.91,
  "reflected": false,
  "message_type": "sms",
  "redactions": ["OTP"],
  "redacted_text": "BDO ALERT: Your account is on hold...",
  "red_flags": [{ "label": "…", "detail": "…", "chunk_id": "lure-account-suspended" }],
  "explanation": "Scam po ito...",
  "next_steps": ["Huwag i-click ang link.", "…"],
  "contacts": [{ "organisation": "BDO Unibank", "hotline": "(02) 8631-8000", "url": "…" }],
  "similar_scams": [{ "text": "…", "scam_type": "bank-impersonation" }],
  "kb_freshness": "2026-08-06",
  "model_id": "bedrock_converse:global.anthropic.claude-sonnet-5"
}
```

Errors return `{ "error": { "code", "message" } }` with user-safe text. The unhandled-error
handler logs `type(exc).__name__` and nothing else — **provider exception text can echo the
request body**, which would leak the input preprocessing exists to protect.

### `POST /api/analyze` is `def`, not `async def` — this is load-bearing

`graph.invoke()` is synchronous and blocks for the full ~40s analysis. Under `async def` it
pins the event loop and every concurrent caller serialises: measured against the deployed
VM, two simultaneous requests returned in **22.1s and 58.7s**, the second having waited out
the first — right at the edge of a 60s gateway timeout, and a third would have blown past
it. Declared as a plain `def`, FastAPI runs it in a threadpool and requests overlap.

`health` and `meta` stay `async` because neither blocks meaningfully.

If a panel opens the URL and three people paste at once, this is the bug you would have hit.

### Preprocessing — `preprocess.py`

Pure functions. No LLM, no I/O. Two jobs.

**Message type:** a bare URL → `url`; text with `From:`/`To:`/`Subject:`/`Reply-To:` headers
→ `email`; anything else → `sms`.

**Redaction**, in this order, each match replaced by its label:

| Pattern | Label |
|---|---|
| 4–8 digits adjacent to `otp` / `code` / `pin` / `verification` | `[OTP]` |
| 13–19 digit runs (card numbers) | `[CARD]` |
| PH mobile: `09xxxxxxxxx`, `+639xxxxxxxxx` | `[PHONE]` |
| 10–16 digit runs (account numbers) | `[ACCOUNT]` |
| Email addresses | `[EMAIL]` |

Two ordering rules matter:

- **`PHONE` before `ACCOUNT`.** A PH mobile number is itself an 11-digit run, so the generic
  account pattern firing first would mislabel every phone number as an account. More
  specific patterns fire first throughout.
- **URLs are shielded first and never redacted.** They are swapped for `\x00URLn\x00`
  placeholders before the digit patterns run and restored afterwards, because a URL can
  contain a long digit run that would otherwise be eaten as a card number. The domain is
  the primary signal the Detector needs — redacting it would blind the whole pipeline.

The OTP replacement rewrites only the captured digits, not the whole match, so
`your OTP is 123456` becomes `your OTP is [OTP]` rather than `[OTP]` — the Detector still
sees that the message *asked for an OTP*, which is itself a red flag.

Output is `Preprocessed(redacted_text, message_type, redactions)`, where `redactions` is a
deduplicated list of **labels only, never values**.

### Configuration — `config.py`

Every tunable is read here and nowhere else.

| Variable | Default | What it does |
|---|---|---|
| `LLM_MODEL` | `bedrock_converse:global.anthropic.claude-sonnet-5` | Any `init_chat_model` string |
| `LLM_MAX_TOKENS` | `4096` | May bound reasoning as well as visible output |
| `CONFIDENCE_THRESHOLD` | `0.70` | Below this, the Detector reflects once |
| `LLM_RETRY_BACKOFF` | `20` | Seconds to wait after a 429 |
| `KB_PATH` | real KB if built, else fixture | `knowledge-base/out/kb.sqlite` |
| `AWS_REGION` | `ap-southeast-1` | Bedrock region |
| `AWS_BEARER_TOKEN_BEDROCK` | *(none)* | Sandbox token. The `_BEDROCK` suffix is required |

Three details that bite:

1. **The `SHIELD_*` names are dead.** They were renamed on 2026-08-06. A leftover
   `SHIELD_MODEL` in your `.env` does not error — pydantic-settings simply does not see it
   and uses the default, so the app runs happily on the wrong model with nothing in the
   logs looking wrong. Update `backend/.env` by hand.
2. **`load_dotenv(ENV_FILE, override=False)` runs at import.** pydantic-settings reads
   `.env` into `Settings` but puts nothing in `os.environ`, and the AWS SDK reads its
   credentials from there. Without this line a valid token in `.env` still fails to
   authenticate. `override=False` keeps an already-exported variable winning over the file.
3. **Settings come from `get_settings()`, not a module-level object.** The `lru_cache` means
   one read per process, and `cache_clear()` lets a test set an env var and see the change.
   A module-level instance would freeze whatever environment existed at first import.

`protected_namespaces=()` is set so the field can be called `model_id`; pydantic otherwise
reserves the `model_` prefix.

### The provider switch — `llm.py`

The only module in the codebase that imports a provider SDK. Two public functions:

```python
def get_model() -> BaseChatModel:
    return init_chat_model(settings.model_id, max_tokens=settings.max_tokens)

def invoke_with_retry(runnable, payload):   # every LLM call goes through here
```

**This project pays for no LLM API.** The Accenture Bedrock sandbox serves Claude under
`anthropic.claude-*` IDs on AWS billing. Do not add a paid provider key or a dependency
that assumes one.

**The region gotcha:** ap-southeast-1 does not serve Claude Sonnet 5 in-region. Only the
**global inference profile** works, hence the `global.` prefix. The bare
`anthropic.claude-sonnet-5` fails from Singapore.

**Never pass sampling parameters** — no `temperature`, `top_p`, `top_k`. This is a
portability rule, not a per-model quirk: providers disagree about which they accept and some
reject them outright, so a parameter that works under one `LLM_MODEL` and 400s under another
defeats the whole point of the switch. Passing none works everywhere. Behaviour is steered
by the prompt.

**Retry lives here and only here.** A full eval run is ~200 calls and the sandbox's rate
limits are undocumented. `is_rate_limit()` matches on the wire status and on wording markers
(`429`, `resource_exhausted`, `rate limit`, `throttl`, …) rather than on exception types,
because each provider raises its own and importing them would break the abstraction.
Backoff escalates as `LLM_RETRY_BACKOFF × attempt` over `MAX_ATTEMPTS = 4`. Non-429 failures
raise immediately — retrying a malformed prompt just burns two minutes and the same quota.

Retry is a separate function rather than folded into `get_model()` because LangChain's
`Runnable.with_retry()` returns a plain `Runnable`, which no longer offers
`with_structured_output()`. **Build the chain first, wrap it last.**

**Gemini was removed on 2026-08-06.** It existed only because the sandbox model list was
unconfirmed. Re-adding any provider is an `uv add` of its langchain package plus an
`LLM_MODEL` string — no code change. (Historical finding worth keeping: Gemini's free tier
granted *zero* quota on `gemini-2.5-pro` — `429 RESOURCE_EXHAUSTED, limit: 0`, not a rate
limit that waiting clears.)

### Running it

```bash
cd backend
uv sync
cp .env.example .env      # paste the sandbox token into AWS_BEARER_TOKEN_BEDROCK
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run python check_bedrock_connection.py     # does the token + model ID actually work
```

First run downloads ~590MB (PyTorch into `.venv`, the ~120MB embedding model into the HF
cache). **Do that today, not on presentation morning.** Warm start is ~13s, because the
embedding model loads once at boot rather than per request.

---

## 6. How the knowledge base works

`knowledge-base/` is Nian's deliverable and arrives from his machine as a subtree.
**Read `out/kb.sqlite`; never author or edit inside that tree.** Until it lands, the backend
falls back to `backend/tests/fixtures/kb_fixture.sqlite` automatically.

### The seven tables

| Table | Rows | Holds |
|---|---|---|
| `sources` | 10 | Every origin: URL, retrieval date, licence, attribution |
| `brand_rebuttals` | 4 | Each impersonated brand's own "we never ask…" statement, verbatim, plus its official hotline and URL |
| `lure_patterns` | 10 | Recurring lure shapes with measured share/count and bilingual trigger phrases |
| `reporting_contacts` | 4 | Where a victim actually reports, in priority order (I-ARC 1326 first) |
| `advisories` | 9 | Full fetched advisory text from brands and government bodies |
| `message_examples` | 1,571 | The de-duplicated corpus, labelled SCAM/LEGIT and tagged |
| `kb_chunks` | **732** | The retrieval surface: everything above, flattened, with bilingual keyword fields and an `embedding` BLOB |

**732 is the number to remember.** `GET /api/meta` returns `chunk_count`, and if it comes
back much smaller, `KB_PATH` silently fell back to the fixture. The app still answers
plausibly on the fixture, which is exactly why that check exists — the failure is invisible
from the UI.

### Where the data comes from

The corpus is [scottleechua/data](https://github.com/scottleechua/data), a public CC BY 4.0
set of PH spam and marketing SMS — 8,255 messages, 1,907 with usable text after the author's
own privacy redaction, collapsing to 1,571 distinct normalised texts after de-duplication.

Advisory content is quoted **verbatim** from pages that were actually fetched, with the date
recorded in `content/fetch_log.json`. Several PH sites (GCash Help Center, UnionBank,
PNP-ACG, NTC) sit behind Cloudflare and 403 scripted requests; those were captured with
browser automation and are marked `ok-browser` — they will not reproduce from
`fetch_sources.py` alone. BSP is absent entirely because `bsp.gov.ph` served a maintenance
notice on every attempt, and the rule is that an unverifiable hotline does not ship.

**The provenance rule:** nothing is written from memory. A brand whose statement could not
be sourced gets no row. An invented quote attributed to a bank is the worst failure this
knowledge base could contain.

### Retrievability — the two exclusions that matter

`message_examples` has `retrievable` and `eval_holdout` columns, enforced by CHECK
constraints in the schema:

- **`LEGIT` rows are never retrievable.** 844 hard negatives are stored but never served.
- **Eval-set rows are held out.** All 55 gold-labelled eval messages matched the corpus;
  53 rows are held out after de-duplication, leaving **692 retrievable messages**.

This is pipeline invariant 5. Retrieving the test set means measuring nothing. The backend
enforces it a second time in SQL at load — see `store.py` below — so it holds even against a
KB build that got the flags wrong.

### Embeddings: the KB ships without them, and we add them

`kb_chunks.embedding` is `NULL` for all 732 rows when the KB arrives. Picking an embedding
provider was not that deliverable's call.

The backend populates it on first load with our local model, **writing to a
backend-owned copy** at `backend/var/kb_embedded.sqlite`, refreshed whenever Nian's build is
newer (`store.py::_writable_path`). Nian's source tree is never written to. This is the one
change we make to KB *data*, and it happens entirely inside `backend/`.

### Rebuilding it (Nian's flow, recorded here for completeness)

```bash
python3 -m venv knowledge-base/.venv
knowledge-base/.venv/bin/pip install -r knowledge-base/requirements.txt
knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
knowledge-base/.venv/bin/python knowledge-base/scripts/verify_kb.py   # must exit 0
```

`build_kb.py` writes `out/kb.sqlite`, `out/kb_seed.postgres.sql`, `out/build_report.json`,
and regenerates `ATTRIBUTION.md`. The build is not done until `verify_kb.py` exits 0.

---

## 7. How we use LangGraph

### Why LangGraph and not a plain chain

Because of the cycle. `detect → reflect → detect` is a loop, and a LangChain chain is a
DAG — it cannot express one. Everything else in the pipeline would have been a chain. If
somebody asks "did you need LangGraph or did you just want it on the slide," the loop is the
answer, and it is a loop the mentor specifically asked for (ruling 6).

### The state

`GraphState` is a `TypedDict` with `total=False`, so nodes return partial dicts and LangGraph
merges them.

```python
class GraphState(TypedDict, total=False):
    redacted_text: str
    message_type: Literal["sms", "email", "url"]
    redactions: list[str]              # labels only, never values
    output_language: Literal["en", "tl"]

    concepts_en: list[str]             # ← retrieve
    retrieved: list[Chunk]             # ← retrieve

    verdict: Verdict                   # ← detect
    confidence: float                  # ← detect
    first_verdict: Verdict             # ← detect, first pass only — the eval reads it
    first_confidence: float            # ← detect, first pass only
    red_flags: list[RedFlag]           # ← detect
    reflection_count: int              # ← detect / reflect
    low_confidence_reason: str | None  # ← detect, consumed by reflect

    advice: Advice                     # ← advise
```

**What is deliberately absent: the raw unredacted input.** That is pipeline invariant 1, and
it is enforced by construction — the field does not exist, so no node can accidentally carry
it — rather than by remembering to strip it later.

`first_verdict` / `first_confidence` exist purely so the eval's threshold sweep can
reconstruct both passes from a single run. See §9.

### The wiring — `graph/build.py`

```python
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "detect")
graph.add_conditional_edges("detect", route, {"advise": "advise", "reflect": "reflect"})
graph.add_edge("reflect", "detect")
graph.add_edge("advise", END)
```

The conditional edge, with its bound:

```python
def route(state):
    if state["confidence"] >= bound:            return "advise"
    if state.get("reflection_count", 0) >= 1:   return "advise"
    return "reflect"
```

**The second clause is what makes the loop terminate**, and it is the single most important
line in the graph. A loop that cannot terminate is a demo failure — invariant 4. Worst case
is four LLM calls per request, and `test_graph.py` asserts that a *second* low-confidence
pass still routes to `advise`.

`reflect` is **not an LLM call.** It is three lines that increment `reflection_count`. The
work happens when `detect` re-runs and sees a non-zero count, at which point it appends
`prompts/reflect.md` to its own prompt, carrying the prior verdict, its confidence, and the
stated doubt. That is what makes retry differ from a plain re-run.

`build_graph(model, store, threshold=None)` takes its dependencies as arguments. That is why
`test_graph.py` can pass `FakeListChatModel` and a fixture store and test control flow with
no network, no cost, and no nondeterminism.

`main.py` wraps construction in `@lru_cache` so the graph and the `ChunkStore` — which loads
the embedding model and the whole KB into memory — are built once per process, at first
request, not per call.

### The nodes

Each node is a **factory** returning a closure: `make_retrieve(model, store)`,
`make_detect(model)`, `make_advise(model)`. The factory loads the prompt file once at
build time; the closure runs per request. Dependencies are explicit, and nothing reads a
global.

**`retrieve`** — sends `prompts/retrieve.md` with the message, expects a JSON array of 3–6
short English concepts back, then calls `store.search(concepts + [redacted_text], top_k=6)`.
If the model returns unparseable output, `concepts` falls back to `[]` and the raw redacted
text alone still drives retrieval — a bad concept extraction degrades the search, it does
not fail the request.

**`detect`** — renders `prompts/detect.md` with the retrieved chunks, message type,
redaction labels, redacted text, and output language; appends `prompts/reflect.md` on a
reflection pass; validates the reply into a `DetectOutput` pydantic model. On the first pass
only, it also writes `first_verdict` and `first_confidence`.

**`advise`** — gathers contacts (see below), renders `prompts/advise.md`, validates into
`AdviseOutput`, and returns an `Advice` carrying the model's explanation and next steps
alongside the **Python-selected** contact list.

### JSON parsing — `nodes/common.py`

`parse_json_reply()` exists because models wrap JSON in code fences or prose despite being
told not to. It does two things:

1. Bedrock Converse returns content as a **list of blocks**, not a string. Only the text
   blocks are joined.
2. Strips ```` ```json ```` fences, tries `json.loads`, and on failure falls back to
   `raw_decode` from the first `{` or `[` — which tolerates trailing prose.

### The prompts

`backend/app/prompts/*.md` — never string literals in Python. **They are product logic.**
Treat edits to them as code changes and run the eval afterwards.

| Prompt | Job |
|---|---|
| `retrieve.md` | Message → 3–6 English red-flag concepts. Tactics, not surface words. |
| `detect.md` | The four guardrail rules, the four verdicts, the JSON schema, and the output-language instruction for red-flag text |
| `reflect.md` | "Address the stated doubt directly… an honest UNCLEAR is better than manufactured confidence." |
| `advise.md` | Register control, the verbatim-contacts rule, and the action-not-advice rule |

The four guardrail rules in `detect.md`, verbatim in spirit:

1. Never claim certainty. There is no SAFE verdict.
2. Every red flag cites a `chunk_id`, or is explicitly marked as unsupported by the KB.
3. Never tell the user to click, reply, or call anything from the message.
4. When genuinely unsure, emit `UNCLEAR` and let confidence reflect the doubt.

`advise.md` specifies register **explicitly**, because a model told to "reply in Tagalog"
drifts toward textbook register (*panganib*, *pagpapatunay*) that is harder for the target
user to read than Taglish. It names the substitutions: not *panganib* → *delikado*, not
*pagpapatunay* → *pag-verify*, and brand names, hotlines, and app names are never translated.

---

## 8. How we use RAG

### The three pieces

```
query side:   redacted text ──LLM──► English concepts ──┐
                            └──────────────────────────►├─► embed ─► cosine ─► top 6 chunks
corpus side:  kb_chunks.text ─────────► embed (once, cached in the DB)
```

### The cross-lingual hop is the whole point

The corpus is English. A user pastes Taglish. Embedding "Nag-expire na po ang GCash account
ninyo, i-click ito" directly against English advisories relies on the multilingual model
getting lucky.

So the `retrieve` node inserts an LLM step first: rewrite the message into English red-flag
**concepts** describing what it is *doing* — `"claims account suspended"`, `"urgency
deadline"`, `"shortened link"` — not what it says. Those concepts are what get embedded.
This closes open question 3 from the proposal: the Taglish→English hop happens *before*
retrieval, so a Taglish query reaches an English corpus through meaning rather than through
embedding luck.

The redacted text is embedded **alongside** the concepts, so a surface match (a brand name,
a distinctive phrase) still counts even when concept extraction is weak.

### The embedder — `retrieval/embedder.py`

`intfloat/multilingual-e5-small`, 384 dimensions, ~120MB, loaded once behind an `lru_cache`.

Two things about it:

- **e5 models require prefixes.** Queries are embedded as `query: {text}` and passages as
  `passage: {text}`. Embedding without the prefixes measurably degrades retrieval, so
  `embed_queries()` and `embed_passages()` are separate functions and neither takes a flag.
- **It is local and provider-independent.** No network after the first download, so the demo
  survives a flaky venue connection for everything except the LLM call itself — and
  switching `LLM_MODEL` never forces a KB re-embed. Embeddings are **not** the chat
  provider; keeping them separate is a deliberate architectural boundary.

Vectors are normalized at encode time, so cosine similarity is a plain dot product.

### The store — `retrieval/store.py`

The **only** semantic-search surface in the codebase.

**On load**, it runs one SQL query that joins `kb_chunks` to `message_examples` and
`lure_patterns` and applies the exclusion:

```sql
WHERE c.parent_type != 'message_example'
   OR (m.retrievable = 1 AND m.eval_holdout = 0 AND m.label != 'LEGIT')
```

Excluded rows are never loaded into memory, so **no query can return them** — the eval
holdout and the LEGIT negatives are unreachable by construction, not by filtering at search
time where a future refactor could drop the filter.

Any chunk still missing an embedding is embedded with the local model and written back to
the DB, so the cost is paid once ever, not once per boot.

**On search**:

```python
scores = (query_vectors @ self._vectors.T).max(axis=0)
order  = np.argsort(scores)[::-1][:top_k]
```

Each chunk is scored by its **best** match across the query set — the redacted text and each
concept vote independently, and a chunk only needs to match one of them strongly. A mean
would let four weak concepts drown out one exact hit.

Full scan in numpy, no index. The KB is 732 rows; an ANN index would be complexity in
exchange for microseconds.

### What RAG deliberately does **not** touch: contacts

This is pipeline invariant 2 and the one worth stating out loud at the panel.

Hotlines and official URLs come from `retrieval/contacts.py`, which does **primary-key
SELECTs and nothing else**. `known_brands()`, `rebuttal_for_brand(brand_id)`,
`top_contacts(n)` ordered by `priority`. No embeddings, no similarity, no LLM.

Brand detection in `advise.py` is a deterministic substring scan of the redacted text
against `brand_rebuttals.brand_name`. Matched contacts are injected into the Advisor prompt
as data with an explicit instruction to reproduce them character for character — **and the
`contacts` array in the API response is the Python-selected list, not the model's echo of
it.** The model cannot corrupt a hotline even if it tries.

`contacts.py` exists as a separate module from `store.py` for exactly this reason: the type
system keeps semantic search away from phone numbers. A fuzzy-matched hotline handed to a
panicking user is the one failure this product cannot survive.

---

## 9. Testing and evaluation

### Three layers, three homes

| Layer | Tool | Location | Runs against |
|---|---|---|---|
| Backend unit | pytest | `backend/tests/` | Fixture KB, fake LLM |
| Frontend component | Vitest | `frontend/src/**/*.test.tsx` | jsdom |
| E2E | Cypress | `qa/cypress/e2e/` | Stubbed API |
| E2E smoke | Cypress | `qa/cypress/e2e/smoke/` | **Live backend + real LLM** |

**One spec file per feature**, not one per layer. A failing spec should name the broken
feature in its filename.

Backend modules: `test_config` (every var read, defaults hold, unrelated vars ignored),
`test_llm` (no sampling params, 429 detection across provider wordings, retry escalation and
cap), `test_preprocess` (each pattern, URL preservation, type detection), `test_retrieval`
(Taglish query hits an English advisory; LEGIT and eval rows never appear), `test_graph`
(reflection fires exactly once, high confidence skips it, a second low pass still
terminates), `test_api` (`TestClient` response shape, both languages, malformed input),
`test_eval` (the sweep arithmetic). The deployment verification on 2026-08-06 recorded
**75 passed** with the static mount in place.

`test_graph.py` is the one that matters most: the reflection loop is the only place this
system can hang, and `FakeListChatModel` lets it be tested without network, cost, or
nondeterminism.

**E2E is stubbed by default.** A real analysis is 3–4 LLM calls at ~40s and real sandbox
quota. `cy.intercept` with fixtures covers all four verdicts and every error state, fast and
deterministically. The single live spec in `smoke/` is excluded from `npm run cy:run` and
exists to catch frontend/API contract drift — the one thing stubs structurally cannot see.
Run it before the demo, not on every save.

Default Cypress viewport is 390×844, because the elderly user is on a phone.

```bash
cd qa && npm run e2e          # stubbed suite, starts the frontend for you
cd qa && npm run cy:open      # interactive
cd qa && npm run e2e:smoke    # LIVE — costs real tokens, needs the backend up
```

### The eval harness

```bash
cd backend && uv run python eval/run_eval.py [--limit N]
```

All 55 gold-labelled messages through the full pipeline, with the reflection threshold
**forced to 0.95**, so nearly every message produces both a first and a second pass. That is
the trick that makes a threshold sweep computable from a single run:

```
verdict(t) = second-pass verdict  where first-pass confidence < t
             else first-pass verdict
```

which is precisely why `first_verdict` and `first_confidence` are preserved in graph state.

Gold labels are binary; the pipeline is four-way. For metrics, `SCAM` and `LIKELY_SCAM`
count as scam; `UNCLEAR` and `LIKELY_LEGIT` count as not-scam. **Counting `UNCLEAR` against
the scam class is the conservative choice** — an `UNCLEAR` on a real scam is a miss the user
pays for — and the per-message table keeps the four-way verdicts visible.

Output is markdown in `eval/results/`: confusion matrix, accuracy/precision/recall/F1, a
sweep from 0.50 to 0.95 in 0.05 steps showing how many messages would reflect and what
accuracy results, and a per-message table. ~200 LLM calls per run; `llm.py` owns the backoff.

Running it twice under different `LLM_MODEL` values is the model bake-off — "how did you
choose your model" answered with measurements rather than a spec sheet.

**Honest framing for the deck:** the threshold is calibrated on the same 55 messages we
report accuracy on. That is fitting to the test set. Say so rather than presenting it as
held-out accuracy.

---

## 10. Where it is deployed

**Target:** the DLSU ALTDSI GPU VM, `ALTDSI-GPU-R05` (A100-PCIE-40GB).

| | |
|---|---|
| SSH | `ssh root@altdsidccf.dlsu.edu.ph -p 32051` |
| Public URL | `http://altdsidccf.dlsu.edu.ph:32050` → VM port 80 |
| Install root | `/root/kalasag` — everything, nothing system-wide |
| Process | one `uvicorn` in a tmux session named `kalasag` |

### The shape: one origin, one process, one port

The VM exposes exactly one HTTP port, and that constraint decides the architecture — happily
onto the simplest option. **FastAPI serves the built frontend as static files alongside
`/api/*` on port 80.** The mount, at the very end of `main.py`:

```python
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "static"

if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
```

Two guards, both load-bearing:

- **Registered last.** FastAPI matches routes in registration order; a mount at `/` declared
  earlier would swallow every `/api/*` route.
- **`is_dir()` guard.** `StaticFiles` raises at *construction* if the directory is missing.
  `backend/static/` is gitignored and absent in dev and CI, so without the guard `uv run
  pytest` would break on every machine that has not built the frontend. With it, the mount
  is simply inert everywhere except a deployed box — **which is why there is no deploy
  branch.** The change carries no content `main` does not, and a deploy branch would cost a
  second merge on every feature.

### Why not Vercel for the frontend

Considered and rejected, in order of how fatal:

1. **Mixed content.** Vercel serves HTTPS; the VM serves plain HTTP on a non-standard port.
   A browser on an HTTPS page blocks every `fetch` to an HTTP backend, silently, with no
   user override. This alone ends it.
2. **No TLS path.** Fixing (1) needs a certificate for `altdsidccf.dlsu.edu.ph`, a domain we
   do not control, on port 32050. Not in a week.
3. **It would add work** — a CORS allowlist, an API base URL config, a second deploy target
   — all to make the app strictly worse.

### Verified on 2026-08-06

| Check | Result |
|---|---|
| SSH 32051 reachable off-campus | yes |
| VM → Bedrock egress | yes (HTTP 404 over validated TLS — a *blocked* path returns `000`) |
| Bedrock token + `global.` model ID from the VM | yes — `check_bedrock_connection.py` returned `pong` |
| VM port 80 | free |
| VM disk | 251 GB total, 131 GB free |
| Install footprint | 5.0 GB under `/root/kalasag` |
| Public URL end to end | yes — `SCAM` @ 0.98 in 40.6s, OTP redacted, real hotlines returned |

`docs/DEPLOYMENT.md` is the full runbook, including first-time install. What follows is the
part you will actually run again.

---

## 11. Redeploying after a change lands on main

This is the loop you run every time a feature is merged. **Nine commands, about two
minutes**, most of it the frontend build.

### Why git is not the transport

The VM has no clone of the repo, and giving it one would not help. Three files the app
cannot run without are gitignored and would never survive a `git pull`:

- `knowledge-base/out/kb.sqlite` — the real KB
- `backend/.env` — the Bedrock token
- `backend/static/` — the built frontend

So you `git pull` **on the Mac**, build there, and ship one archive. Everything needed,
nothing else, and it either arrives or it does not.

### Step 1 — get main, on the Mac

```bash
cd /Users/achibukz/Code/GitHub/Elderly-Scam-Shield
git checkout main && git pull
```

### Step 2 — rebuild the frontend and stage it

```bash
cd frontend && npm run build && cd ..
rm -rf backend/static && cp -R frontend/dist backend/static
```

**Not optional, even for a backend-only change.** The archive ships `backend/static/`
wholesale, so skipping the build re-deploys whatever UI was in that folder last time. If
your merge included a frontend commit and you skip this, you deploy the new backend against
the old UI and the smoke spec is the only thing that would catch it.

Build on the Mac, not the VM — it avoids installing Node and a `node_modules` tree on the VM
for a one-time build.

### Step 3 — build the archive

```bash
COPYFILE_DISABLE=1 tar czf ~/Desktop/kalasag-deploy.tgz \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.venv' \
  --exclude='backend/eval/results' \
  backend/app backend/tests backend/eval backend/pyproject.toml backend/uv.lock \
  backend/.env backend/.env.example backend/static backend/check_bedrock_connection.py \
  knowledge-base/out/kb.sqlite docs/DEPLOYMENT.md
```

About **1 MB**. Notes on the flags:

- `COPYFILE_DISABLE=1` suppresses the `._` AppleDouble files macOS otherwise scatters
  through the archive.
- The excludes matter: `backend/.venv` is 903 MB of **macOS** binaries and
  `frontend/node_modules` another 138 MB. Neither is usable on Linux.
- **The paths are relative to the repo root and must stay that way.** `config.py` resolves
  the KB as `<backend>/../knowledge-base/out/kb.sqlite`, so flattening the structure sends
  it silently back to the fixture.

**Do not drag the project folder into the Remote-SSH explorer instead.** Beyond the 1 GB of
unusable binaries, Finder hides dotfiles — select-all inside a folder does not pick up
`backend/.env` unless you have pressed `Cmd-Shift-.` first, so the single most important
file is the one most likely to be left behind.

### Step 4 — upload

**Remote-SSH way:** open the VS Code remote window, point the Explorer at `/root`, drag
`kalasag-deploy.tgz` in.

**Or one command from the Mac terminal:**

```bash
scp -P 32051 ~/Desktop/kalasag-deploy.tgz root@altdsidccf.dlsu.edu.ph:/root/
```

Delete the local copy when you are done — it contains the Bedrock bearer token in cleartext.

### Step 5 — extract over the top, on the VM

In the Remote-SSH terminal:

```bash
tar xzf /root/kalasag-deploy.tgz -C /root/kalasag    # overwrites in place
rm /root/kalasag-deploy.tgz
```

This never touches `/root/kalasag/.local/` or `/root/kalasag/backend/.venv/`, because
neither is in the archive. **A redeploy therefore costs one megabyte, not a re-download of
torch.**

Run `uv sync` again **only if `pyproject.toml` or `uv.lock` changed** in the merge:

```bash
source /root/kalasag/.local/env.sh
cd /root/kalasag/backend && uv sync
```

One caveat: extract-over-the-top overwrites and adds but never deletes. If the merge
**renamed or removed** a source file, the stale copy lingers on the VM. Harmless for a
one-week demo; if it ever matters, `rm -rf /root/kalasag/backend/app` before extracting.

### Step 6 — restart the server

```bash
tmux attach -t kalasag
# Ctrl-C to stop uvicorn
source /root/kalasag/.local/env.sh
cd /root/kalasag/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 80
# then detach — see §12
```

**`source` is not optional.** Every new shell — including a fresh tmux window — has never
seen those exports, and without them `uv` is not on `PATH` at all.

### Step 7 — verify, from the Mac

```bash
curl http://altdsidccf.dlsu.edu.ph:32050/api/health     # {"status":"ok"}
curl http://altdsidccf.dlsu.edu.ph:32050/api/meta       # chunk_count MUST be 732
```

Then open `http://altdsidccf.dlsu.edu.ph:32050` and **run one real analysis end to end**.
Nothing short of a full request proves the deployment — health and meta never touch the LLM.

Hard-refresh the browser (`Cmd-Shift-R`) before judging the UI, or you will be looking at
the cached old bundle and blaming the deploy.

If you changed anything around concurrency, fire two requests at once; both should land near
40s rather than one waiting out the other.

### The whole thing, copy-pasteable

```bash
# on the Mac
cd /Users/achibukz/Code/GitHub/Elderly-Scam-Shield && git checkout main && git pull
cd frontend && npm run build && cd ..
rm -rf backend/static && cp -R frontend/dist backend/static
COPYFILE_DISABLE=1 tar czf ~/Desktop/kalasag-deploy.tgz \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.venv' \
  --exclude='backend/eval/results' \
  backend/app backend/tests backend/eval backend/pyproject.toml backend/uv.lock \
  backend/.env backend/.env.example backend/static backend/check_bedrock_connection.py \
  knowledge-base/out/kb.sqlite docs/DEPLOYMENT.md
scp -P 32051 ~/Desktop/kalasag-deploy.tgz root@altdsidccf.dlsu.edu.ph:/root/

# on the VM
tar xzf /root/kalasag-deploy.tgz -C /root/kalasag && rm /root/kalasag-deploy.tgz
tmux attach -t kalasag     # Ctrl-C, then:
source /root/kalasag/.local/env.sh && cd /root/kalasag/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 80
```

---

## 12. tmux — the operations you actually need

The server runs inside tmux so it survives your SSH session closing, and so you can watch
the request log live during the presentation. That second reason matters more than you would
expect when a demo misbehaves.

| What | Command |
|---|---|
| Create the session (first time) | `tmux new -s kalasag` |
| List sessions, and whether attached | `tmux ls` |
| Reattach | `tmux attach -t kalasag` |
| Detach, from inside | `Ctrl-b` then `d` |
| Detach, from another terminal | `tmux detach -s kalasag` |
| Scroll back through the log | `Ctrl-b` then `[`, then arrows / `PgUp`; `q` to exit |
| Stop the server | attach, then `Ctrl-C` |
| Kill the session entirely | `tmux kill-session -t kalasag` |

### The VS Code gotcha

**`Ctrl-b` is intercepted by VS Code's own keybindings**, so the detach prefix often does
nothing in the integrated Remote-SSH terminal. Two ways around it:

1. Open a **second** terminal in the same remote window (the `+` button in the terminal
   panel) and detach from outside: `tmux detach -s kalasag`.
2. Or unbind `Ctrl-b` in VS Code's keyboard shortcuts.

Verify with `tmux ls`. The line ends with `(attached)` while a client is connected and drops
that suffix once you have detached — that absence is your confirmation it is safe to close
VS Code with the server still running.

### The other Remote-SSH gotcha

**The Remote-SSH terminal hard-wraps pasted input at roughly 70 characters and turns the
wrap into a real newline.** A multi-line heredoc gets shredded. A long `export` splits into a
bare `export` plus an unexported assignment — which looks completely fine in `cat` but leaves
the variable out of the environment.

So: paste long commands **one line at a time**, and verify environment variables with
`env | grep -E 'UV_|HF_HOME'` rather than `cat`, because only `env` proves they were
actually exported.

### Detach vs. close

Detaching leaves uvicorn running. Closing the VS Code window while attached also leaves it
running — tmux does not care that the client vanished. What kills it is `Ctrl-C` inside the
session or `tmux kill-session`.

### Teardown after the presentation

The app has **no authentication** and anyone with the URL can spend sandbox quota. Bring it
down when you are done:

```bash
tmux kill-session -t kalasag
rm -rf /root/kalasag
```

That is the whole removal, because the install redirected uv's cache, uv's managed Python,
and the HuggingFace cache into `/root/kalasag/.local/` rather than letting them scatter
across `~/.cache` and `~/.local/share`. Confirm with `du -sh ~/.cache ~/.local`.

Then **rotate `AWS_BEARER_TOKEN_BEDROCK`** in the Accenture sandbox. A copy of it sat in
plaintext in `/root/kalasag/backend/.env` on a shared university machine, readable by anyone
with root on that box.

---

## 13. The invariants — do not break these

Five rules. Breaking one is a correctness bug, not a style choice. They are in `CLAUDE.md`
and repeated here because they are the parts a well-meaning refactor is most likely to
quietly undo.

1. **Raw user input never enters graph state and is never logged.** `preprocess.py` redacts
   before anything reaches an LLM; only redacted text moves forward. This survives
   deployment too — uvicorn's access log records the request line only, never the body, so
   **do not add `--log-level trace`** to debug something.
2. **Hotlines and official URLs are read by key, never retrieved semantically.** They come
   from `brand_rebuttals` and `reporting_contacts` and are passed to the Advisor as data.
3. **The Detector never claims certainty.** There is no `SAFE` verdict. Even `LIKELY_LEGIT`
   renders with "verify independently before acting."
4. **The self-reflection loop is bounded at one pass.** A loop that cannot terminate is a
   demo failure.
5. **Eval-set messages are held out of retrieval.** Retrieving the test set means measuring
   nothing.

Two more that are not on that list but behave like it:

- **Only `llm.py` constructs a model, and it passes no sampling parameters.**
- **`POST /api/analyze` stays `def`, not `async def`.**

---

## 14. Troubleshooting

**`chunk_count` is small (not 732).** `KB_PATH` fell back to the fixture. The KB did not
land in the archive, or the directory structure got flattened. The app answers plausibly on
the fixture, which is why this is checked explicitly — the failure is invisible from the UI.

**Auth error on the first analysis.** No `backend/.env`, or `AWS_BEARER_TOKEN_BEDROCK` is
blank. It is gitignored by design, so pulling the repo never gives you one. Check with
`uv run python check_bedrock_connection.py`.

**Model works locally, 400s from the VM (or vice versa).** The `global.` prefix. Bare
`anthropic.claude-sonnet-5` fails from ap-southeast-1.

**Auth silently falls back to SigV4 and fails.** The env var is not named
`AWS_BEARER_TOKEN_BEDROCK`. botocore looks for that exact name.

**A setting has no effect.** You are using a `SHIELD_*` name. They were renamed on
2026-08-06 and the old ones fail silently into the default.

**400 mentioning `temperature` or `top_p`.** Something passed a sampling parameter. Only
`llm.py` should construct the model.

**429 / rate limited.** `llm.py` backs off and retries. Raise `LLM_RETRY_BACKOFF` if an eval
run keeps tripping it.

**`uv sync` fails on torch.** Python is outside 3.13–3.14. Check `uv run python --version`.

**Backend takes ~13s to start.** Expected. The embedding model loads once at boot, never per
request.

**Frontend shows a network error in dev.** The backend is not on `:8000`. Vite proxies
`/api` there.

**The UI did not change after a redeploy.** Either `npm run build` was skipped, or your
browser is serving the cached bundle. Hard-refresh first.

**Two simultaneous requests, one takes ~60s.** The threadpool fix regressed —
`POST /api/analyze` is `async def` again.

---

## 15. Known limitations, stated honestly

Worth having ready, because the panel will ask.

- **The confidence threshold is calibrated on the same 55 messages we report accuracy on.**
  That is fitting to the test set, and we say so rather than calling it held-out accuracy.
- **No OCR.** Users receive scams as screenshots constantly. Presented as future work, not
  built.
- **The corpus is public SMS spam data**, not a purpose-collected elderly-victim dataset.
  Casino promos dominate it (420 of 727 SCAM rows) because that is what the source contains.
- **`UNCLEAR` counts against the scam class** in the metrics. Conservative by choice.
- **~40s per analysis.** Three to four sequential LLM calls. Acceptable for a considered
  decision, not for an interruption.
- **No authentication on the deployment.** Anyone with the URL spends sandbox quota. It
  comes down after the demo.
- **Deviations from mentor rulings are allowed; doing them silently is not.** If we
  contradict `docs/2026-07-29-capstone-mentor-consultation.md`, the deviation and its
  defence get written down.

---

## 16. Team

Aki (Lead, QA) · Allen (Tech) · Nian (Domain / knowledge base) · James (UX) · Lui (Scribe)

Mentor: Rozelle Samonte, Accenture.

Message corpus: [scottleechua/data](https://github.com/scottleechua/data), CC BY 4.0.
Advisory content is quoted verbatim from BSP, NPC, DICT, PNP-ACG, and bank/e-wallet fraud
pages — see `knowledge-base/ATTRIBUTION.md`, which is generated from the `sources` table on
every build and must not be edited by hand.
