# Tasks — Kalasag

Ordered by dependency, not by day. Build a thin vertical slice first (T1–T5), then replace stubs one node at a time. Something demoable exists from T5 onward.

**Status 2026-08-06:** T0–T17 are done on the `prototype1` branch — full pipeline live on Bedrock Claude Sonnet 5, real KB integrated (Nian's build landed the same day), frontend complete, all three test layers green (75 pytest / 16 Vitest / 52 Cypress). The eval harness (T17) is built but the ~200-call live run has not been executed. Remaining: T18 (calibrate), T19 (bake-off), T20b (live smoke), T21 (runbook), T22 (deck).

Each task states its verification. A task is not done until its verify step passes.

Owner tags follow the directory ownership map in `CLAUDE.md`.

---

## Vertical slice

### T0 — Confirm what we can actually call · Aki — **DONE 2026-08-06**
Answered: the Accenture Bedrock sandbox serves Claude models via bearer-token auth; `bedrock_converse:global.anthropic.claude-sonnet-5` verified live from ap-southeast-1 (the `global.` inference-profile prefix is required — the bare ID fails in-region). It is now the default and only provider; the Gemini free-tier key was removed the same day and `langchain-google-genai` dropped. See `ARCHITECTURE.md § Provider abstraction`.

### T1 — Backend scaffold and provider switch · Aki
Create `backend/` with `uv`, FastAPI, LangGraph, and `app/llm.py` wrapping `init_chat_model(settings.model_id)`. `config.py` reads `LLM_MODEL`, `LLM_MAX_TOKENS`, `CONFIDENCE_THRESHOLD`, `LLM_RETRY_BACKOFF`, `KB_PATH` from env.

Pass no sampling parameters — providers disagree about which they accept, and any of them breaks the switch.

`llm.py` owns retry-with-backoff on 429. Free tiers rate-limit at roughly 10–15 requests per minute and an eval run is ~200 calls, so this is load-bearing, not defensive.

**Verify:** a one-line script calls the model and prints a response, on two different `LLM_MODEL` values, with no code change.

### T2 — Pull the embedding model · Aki
Add `sentence-transformers`, load `intfloat/multilingual-e5-small`, embed a throwaway string.

Do this now, not later. It is a ~120MB download and it must not be the thing that fails on presentation morning.

**Verify:** embedding returns a 384-length vector; second run loads from cache with no network.

### T3 — Fixture knowledge base · Aki
`backend/tests/fixtures/make_fixture.py` builds `kb_fixture.sqlite` against Nian's seven-table schema (documented in `docs/superpowers/specs/2026-08-05-scam-shield-knowledge-base-design.md`). Seed ~20 chunks: the four bank-impersonation lure patterns, casino, package, prize, two brand rebuttals, and I-ARC + PNP-ACG contacts.

This unblocks everything downstream whether or not the real KB arrives.

**Verify:** fixture builds; `sqlite3` shows all seven tables; every chunk has a resolvable `source_id`.

### T4 — API skeleton with a stubbed graph · Aki
`POST /api/analyze` accepts `{text, language}` and returns the full response shape from `ARCHITECTURE.md` with hardcoded values. `GET /api/health`, `GET /api/meta`.

**Verify:** `curl` returns the documented JSON; `test_api.py` asserts the shape.

### T5 — Frontend skeleton end to end · James
Input, submit, verdict card, next steps, red flags, language toggle. Calls the real backend.

Every element the E2E specs query needs its `data-testid` from `qa/TEST-PLAN.md § Spec map` — `message-input`, `submit`, `verdict`, `next-steps`, `red-flags`, `lang-en`, `lang-tl`, `uncertainty`, `reset`.

**Verify:** paste text in the browser, see the stubbed verdict render in both languages. **This is the first demoable build — tag it.**

---

## Real pipeline

### T6 — Preprocessing · Aki
`preprocess.py`: message-type detection and PII redaction per the table in `ARCHITECTURE.md`. Pure functions, no LLM, no I/O.

Raw input must not be returned, logged, or stored.

**Verify:** `test_preprocess.py` covers each redaction pattern, URL preservation, and all three message types.

### T7 — Retrieval · Aki
`embedder.py`, `store.py`, `contacts.py`. Embed the fixture KB's chunks on first build; cosine top-k over the loaded vectors. `contacts.py` does keyed lookups only — no similarity search touches it.

Filter `retrievable = 1`.

**Verify:** `test_retrieval.py` — a Taglish query retrieves an English advisory; no `LEGIT` row is ever returned; keyed lookup returns an exact hotline.

### T8 — Graph state and wiring · Aki
`state.py` and `build.py`. Nodes stubbed; the conditional edge and its bound are real.

**Verify:** `test_graph.py` with `FakeListChatModel` — low confidence reflects exactly once, high confidence goes straight to `advise`, and a second low-confidence pass still terminates.

### T9 — Retrieve node and prompt · Aki
`prompts/retrieve.md` — rewrite the message into 3–6 English red-flag concepts. `nodes/retrieve.py` embeds concepts plus the redacted text and populates `retrieved`.

**Verify:** a Taglish casino message yields English concepts and retrieves the casino lure pattern.

### T10 — Detect node, guardrail prompt, structured output · Aki + Allen
`prompts/detect.md` carrying the four guardrail rules from `ARCHITECTURE.md`. Structured JSON output: verdict, confidence, red flags with `chunk_id`, low-confidence reason.

**Verify:** returns valid structured output on 5 sample messages; never emits a `SAFE` verdict; every red flag cites a chunk or states none matched.

### T11 — Reflection prompt · Allen
`prompts/reflect.md`. Feeds back the prior verdict, its confidence, and why it was low, then asks whether the judgment stands. Must differ from a plain re-run — that was the mentor's specific ruling.

**Verify:** on a deliberately ambiguous message, the two passes produce visibly different reasoning.

### T12 — Advise node and register control · Aki
`prompts/advise.md`. Explanation and next steps in the selected language. Contacts injected as data with an instruction to reproduce them verbatim.

Register rules per `DESIGN.md`: plain Taglish, not textbook Tagalog.

**Verify:** same message in `en` and `tl` produces two natural outputs; the hotline in the output matches the KB byte for byte.

### T13 — Wire the real graph into the API · Aki
Replace the T4 stub. Error handling returns user-safe messages and never echoes the request body.

**Verify:** the frontend from T5 now renders a real analysis end to end.

---

## Product surface

### T14 — Full UI per DESIGN.md · James
All four verdict treatments, collapsed similar-scams and analysed-message sections, uncertainty line, analysing state with step labels, freshness badge from `/api/meta`.

**Verify:** every state in the "States to build" table renders; no state is unreachable or unstyled.

### T15 — Accessibility pass · James
Every rule in the `DESIGN.md` accessibility table.

**Verify:** contrast checked with a tool; keyboard-only run through a full analysis; 200% zoom with no horizontal scroll; `<html lang>` follows the toggle.

### T16 — i18n completeness · James + Lui
Every string in `i18n.ts` in both languages. No hardcoded copy in components.

**Verify:** grep components for literal user-facing strings; a native speaker reviews the Tagalog set.

### T16b — Component tests · James
Colocated `*.test.tsx` per component, Vitest. Priority order: `VerdictCard` (all four verdicts, icon-plus-word), `LanguageToggle`, `NextSteps` (contacts verbatim), `ErrorState` (never renders the submitted text).

**Verify:** `npm test` green in `frontend/`.

### T16c — Green the E2E suite · Aki
The specs in `qa/cypress/e2e/` already exist and encode the `DESIGN.md` contract. They fail until T14 lands the `data-testid` attributes and the states they assert.

Do not weaken a spec to make it pass. If a spec is wrong, fix the spec **and** the doc it came from, in the same commit.

**Verify:** `npm run e2e` green in `qa/`.

---

## Evaluation and delivery

### T17 — Eval harness · Aki
`eval/run_eval.py` — all 85 messages through the full pipeline, emitting a `has_link → SCAM` baseline, a confusion matrix, accuracy/precision/recall/F1, a threshold sweep from 0.50 to 0.95, and a per-message table. Markdown out to `eval/results/`. `--language en --limit 15` runs the English spot-check.

**Verify:** produces the report; numbers are internally consistent.

### T18 — Calibrate the threshold · Aki
Read the sweep, pick the threshold, set `CONFIDENCE_THRESHOLD`, record the reasoning.

State plainly on the deck that the threshold is calibrated on the same set the accuracy is reported on. That is fitting to the test set and we say so.

**Verify:** the chosen value is in config and its rationale is written down.

### T19 — Model bake-off · Aki
Run T17 under two or more `LLM_MODEL` values. Compare accuracy, latency, and Tagalog register.

Candidates are whatever the Bedrock sandbox exposes — T0 confirmed Claude Sonnet 5 works; try at least one more `anthropic.claude-*` ID (e.g. Haiku) for a second column. Access is the binding constraint, which is exactly the mentor's framing — this table is our answer to "how did you choose your model."

Gemini is no longer a candidate: its key was removed 2026-08-06 after the sandbox was verified (and `gemini-2.5-pro` never was one — T1 found the free tier grants it zero quota). If a Gemini column is wanted for the deck, re-adding the provider is an `uv add langchain-google-genai` plus a fresh free key — say so rather than presenting a one-provider table as a cross-provider comparison.

Cost is not a comparison axis; every candidate is free to us. Say so rather than leaving an empty column.

**Verify:** side-by-side table; a native speaker ranks the Tagalog output on each.

### T20 — Integrate the real KB · Nian → Aki
Nian delivers `knowledge-base/`. Point `KB_PATH` at `knowledge-base/out/kb.sqlite`, embed its chunks, re-run T17.

If it has not arrived by the time T17 is done, ship on the fixture and say so on the deck.

**Verify:** eval re-runs against the full KB; the leakage gate passes; accuracy is reported on the real corpus.

### T20b — Live smoke run · Aki
Run `npm run e2e:smoke` against the real backend once the KB is in. This is the only check that the frontend and API agree on the response contract.

**Verify:** both smoke specs pass; every documented response key is present.

### T21 — Runbook and backup capture · Aki + Lui
`README.md` with exact setup and run commands, verified on a second machine. Record a screen capture of a full analysis as the offline backup.

**Verify:** a teammate runs the app from the README alone; the capture plays.

### T22 — Deck update · Lui
Fold in the measured accuracy, the threshold rationale, the bake-off table, the guardrail list, and the limitations from `PRD.md`. Correct the three stale claims flagged in the KB spec: dataset licence and label quality are verified; the old seven-category scam taxonomy is disproven by the corpus analysis; "no public labeled Filipino/Taglish scam dataset exists" is false.

**Verify:** every number on the deck traces to an artifact in this repo.

---

## Not doing

Screenshot / OCR input · voice or TTS · deployment · auth · persistence of submissions · dark mode · history. All are stated as future work in `PRD.md`.
