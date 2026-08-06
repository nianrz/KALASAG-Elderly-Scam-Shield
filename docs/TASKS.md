# Tasks — Elderly Scam Shield

Ordered by dependency, not by day. Build a thin vertical slice first (T1–T5), then replace stubs one node at a time. Something demoable exists from T5 onward.

Each task states its verification. A task is not done until its verify step passes.

Owner tags follow the directory ownership map in `CLAUDE.md`.

---

## Vertical slice

### T1 — Backend scaffold and provider switch · Aki
Create `backend/` with `uv`, FastAPI, LangGraph, and `app/llm.py` wrapping `init_chat_model(settings.model_id)`. `config.py` reads `SHIELD_MODEL`, `SHIELD_MAX_TOKENS`, `SHIELD_CONFIDENCE_THRESHOLD`, `SHIELD_KB_PATH` from env.

Do not pass `temperature`, `top_p`, `top_k`, or `budget_tokens` — all four 400 on Claude 5.

**Verify:** a one-line script calls the model and prints a response, on two different `SHIELD_MODEL` values, with no code change.

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
Vite + React + TS + Tailwind. Input, submit, verdict card, next steps, red flags, language toggle. Calls the real backend.

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

---

## Evaluation and delivery

### T17 — Eval harness · Aki
`eval/run_eval.py` — all 55 messages through the full pipeline, emitting a confusion matrix, accuracy/precision/recall/F1, a threshold sweep from 0.50 to 0.95, and a per-message table. Markdown out to `eval/results/`.

**Verify:** produces the report; numbers are internally consistent.

### T18 — Calibrate the threshold · Aki
Read the sweep, pick the threshold, set `SHIELD_CONFIDENCE_THRESHOLD`, record the reasoning.

State plainly on the deck that the threshold is calibrated on the same set the accuracy is reported on. That is fitting to the test set and we say so.

**Verify:** the chosen value is in config and its rationale is written down.

### T19 — Model bake-off · Aki
Run T17 under two `SHIELD_MODEL` values. Compare accuracy, latency, cost, and Tagalog register.

**Verify:** side-by-side table; a native speaker ranks the Tagalog output on both.

### T20 — Integrate the real KB · Nian → Aki
Nian delivers `knowledge-base/`. Point `SHIELD_KB_PATH` at `knowledge-base/out/kb.sqlite`, embed its chunks, re-run T17.

If it has not arrived by the time T17 is done, ship on the fixture and say so on the deck.

**Verify:** eval re-runs against the full KB; the leakage gate passes; accuracy is reported on the real corpus.

### T21 — Runbook and backup capture · Aki + Lui
`README.md` with exact setup and run commands, verified on a second machine. Record a screen capture of a full analysis as the offline backup.

**Verify:** a teammate runs the app from the README alone; the capture plays.

### T22 — Deck update · Lui
Fold in the measured accuracy, the threshold rationale, the bake-off table, the guardrail list, and the limitations from `PRD.md`. Correct the three stale claims flagged in the KB spec: dataset licence and label quality are verified; the old seven-category scam taxonomy is disproven by the corpus analysis; "no public labeled Filipino/Taglish scam dataset exists" is false.

**Verify:** every number on the deck traces to an artifact in this repo.

---

## Not doing

Screenshot / OCR input · voice or TTS · deployment · auth · persistence of submissions · dark mode · history. All are stated as future work in `PRD.md`.
