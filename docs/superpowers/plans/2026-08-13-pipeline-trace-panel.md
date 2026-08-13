---
title: "Plan — Pipeline Trace Panel"
type: plan
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Aki (Lead)
updated: 2026-08-13
tags: [capstone, kalasag, observability, traceability, ui, api, plan]
---

# Pipeline Trace Panel Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Work task-by-task, commit per task, run the stated verification before moving on.

**Goal:** Add a collapsed "How this was analysed" panel to the result screen that shows, for one analysis, what each of the four pipeline stages did and why — Preprocess, Retrieve, Detect, Advise.

**Why now:** The Observability slide claims every verdict traces to a source chunk and every response shows whether it needed a second look. Both are true of the *data*, but the only place a human can see it today is the raw JSON. The panel makes the claim demonstrable on screen in the demo, and it is the answer to "can you show us the reasoning?" without opening devtools.

**Architecture:** No pipeline change. Every value the panel displays is already computed and already in `GraphState`; two of them are simply not copied onto the response. So this is one API-contract widening plus one presentational component. `AnalysedMessage` is the pattern to copy — same collapsed `<details>`, same place in the layout.

**Tech Stack:** Backend — Python 3.14, `uv`, FastAPI, pydantic 2, pytest. Frontend — React 19, TypeScript, Tailwind v4, Vitest. E2E — Cypress 15 in `qa/`.

## Decisions already made — do not relitigate

1. **Confidence and the model's stated doubt are shown, in the trace panel only.** The primary result area still never shows a number. This deviates from `DESIGN.md`'s existing rule and Task 6 records the deviation and its reason. The rule exists because an uncalibrated number confuses a stressed elderly user; that reason does not apply to a panel someone must deliberately open, and confidence is what makes the Detect row worth reading at all.
2. **The panel is closed by default.** An elderly user must never meet it by accident. It is for the caregiver, the panel, and the demo.
3. **Chunk IDs and types only — never chunk text.** `similar_scams` already returns three chunk *texts*; duplicating them would bloat the response and the panel. The trace shows what was retrieved, not what it said.
4. **Both languages, per the existing i18n contract.** No English-only escape hatch, even though the audience skews caregiver.

## Global Constraints

- **Do not touch `backend/app/graph/`, `backend/app/prompts/`, `preprocess.py`, or `llm.py`.** If a task seems to need a pipeline change, stop — the plan is wrong, not the pipeline. Prompt edits in particular require a full eval re-run and are out of scope.
- **Pipeline invariant 1 holds by construction.** The trace reads from `GraphState`, and raw input is never in `GraphState`. Do not add a code path that carries `request.text` into the response.
- **Accessibility rules in `DESIGN.md` § Accessibility are non-negotiable** and are requirement N2. The new panel is subject to all of them — notably the ≥44px tap target on the `<summary>`, and no horizontal scroll at 320px or at 200% zoom. Chunk IDs are long unbroken strings and *will* break the zoom test if they are not wrapped.
- Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`. **No `Co-Authored-By` trailers.**
- Branch is `feat/pipeline-trace`, already created. Local commits only; do not push without asking.
- Every task's verification must pass before the next task starts. `cd backend && uv run pytest`, `cd frontend && npm test`, `cd qa && npm run e2e`.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/app/schemas.py` | API contract | Modify — add `RetrievedChunk`, three fields on `AnalyzeResponse` |
| `backend/app/main.py` | Response assembly | Modify — populate the three new fields from state |
| `backend/tests/test_api.py` | Contract tests | Modify — assert the new fields |
| `frontend/src/api.ts` | Response types | Modify — mirror the new fields |
| `frontend/src/i18n.ts` | All user-facing copy | Modify — add the `trace.*` keys, both languages |
| `frontend/src/components/PipelineTrace.tsx` | The panel | **Create** |
| `frontend/src/components/PipelineTrace.test.tsx` | Component test | **Create** |
| `frontend/src/App.tsx` | Result layout | Modify — render the panel |
| `qa/cypress/fixtures/verdict-*.json` | Stubbed responses (4 files) | Modify — add the new fields |
| `qa/cypress/e2e/analyse/pipeline-trace.cy.ts` | Feature spec | **Create** |
| `qa/cypress/e2e/analyse/verdict-variants.cy.ts` | Verdict specs | Modify — rescope the confidence assertion |
| `docs/DESIGN.md` | UI/UX spec | Modify — component row, copy table, confidence deviation |
| `docs/ARCHITECTURE.md` | API contract | Modify — the `/api/analyze` example |
| `qa/TEST-PLAN.md` | Coverage map | Modify — new spec |

---

### Task 1: Widen the API contract

Three values exist in `GraphState` and are dropped on the floor when the response is built: the English concepts the Retriever extracted, the chunks it returned, and the Detector's own stated reason for doubt. That last one is the single most interesting string the pipeline produces and nothing has ever displayed it.

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**

```python
# schemas.py — new model, placed next to SimilarScam
class RetrievedChunk(BaseModel):
    chunk_id: str
    parent_type: str          # message_example | advisory | lure_pattern | brand_rebuttal
    scam_type: str | None = None


# schemas.py — added to AnalyzeResponse, after similar_scams
    concepts_en: list[str]
    retrieved: list[RetrievedChunk]
    low_confidence_reason: str | None = None
```

```python
# main.py — inside analyze(), alongside the existing `similar` comprehension
    retrieved = [
        RetrievedChunk(
            chunk_id=chunk.chunk_id,
            parent_type=chunk.parent_type,
            scam_type=chunk.scam_type,
        )
        for chunk in state.get("retrieved", [])
    ]
```

Then on the `AnalyzeResponse(...)` call:

```python
        concepts_en=state.get("concepts_en", []),
        retrieved=retrieved,
        low_confidence_reason=state.get("low_confidence_reason"),
```

**Steps:**
- [ ] Add `RetrievedChunk` to `schemas.py` and import it in `main.py`.
- [ ] Add the three fields to `AnalyzeResponse`. `concepts_en` and `retrieved` are non-optional lists — the retrieve node always returns both, and an empty list is a meaningful value (the concept parse failed, or nothing matched).
- [ ] Populate them in `analyze()`.
- [ ] Extend `test_api.py` to assert all three are present on a successful response, that `retrieved` entries carry a non-empty `chunk_id`, and that `concepts_en` is a list of strings.
- [ ] Add a test asserting the response never contains the raw submitted text when the input carried a redactable value — submit a message with an OTP, assert the OTP digits appear nowhere in the serialised response body. This is invariant 1 in CI.

**Verification:**
```bash
cd backend && uv run pytest
```
All tests green, including the existing suite. Then eyeball one real response shape:
```bash
cd backend && uv run python -c "
from fastapi.testclient import TestClient
from app.main import app
print(TestClient(app).post('/api/analyze', json={'text':'test','language':'en'}).json().keys())
"
```
(That call hits the live LLM and costs ~4 calls. Skip it if the sandbox is rate-limited; the pytest suite uses a fake model and is sufficient.)

**Commit:** `feat: expose retrieval concepts, chunk ids and stated doubt on the analyze response`

---

### Task 2: Mirror the contract in the frontend types and add the copy

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/i18n.ts`

**Interfaces:**

```ts
// api.ts
export interface RetrievedChunk {
  chunk_id: string
  parent_type: string
  scam_type: string | null
}

// added to AnalyzeResponse
  concepts_en: string[]
  retrieved: RetrievedChunk[]
  low_confidence_reason: string | null
```

**Copy — add to both `en` and `tl` objects in `i18n.ts`.** `Copy = typeof en` means TypeScript fails the build if `tl` is missing a key, so add them in the same commit.

| Key | English | Tagalog |
|---|---|---|
| `trace.summary` | How this was analysed | Paano ito sinuri |
| `trace.llm` | AI step | AI |
| `trace.noLlm` | no AI | walang AI |
| `trace.preprocess` | Preprocess | Paghahanda |
| `trace.preprocessDetail` | Read the message, worked out what kind it is, and removed sensitive values. | Binasa ang mensahe, tiningnan kung anong klase, at inalis ang mga sensitibong detalye. |
| `trace.type` | Type: {type} | Klase: {type} |
| `trace.removed` | Removed: {labels} | Inalis: {labels} |
| `trace.removedNone` | Nothing sensitive found. | Walang sensitibong nakita. |
| `trace.retrieve` | Retrieve | Paghahanap |
| `trace.retrieveDetail` | Turned the message into English search concepts, then searched the knowledge base. | Ginawang English na concepts ang mensahe, tapos hinanap sa knowledge base. |
| `trace.concepts` | Searched for: | Hinanap: |
| `trace.conceptsNone` | No concepts were extracted; searched with the message text alone. | Walang na-extract na concepts; ang mensahe lang ang ginamit sa paghahanap. |
| `trace.matched` | Matched {n} knowledge-base entries: | {n} tugma sa knowledge base: |
| `trace.detect` | Detect | Pagsusuri |
| `trace.detectDetail` | Weighed the message against those entries and gave a verdict. | Tinimbang ang mensahe laban sa mga entry na iyon at nagbigay ng hatol. |
| `trace.confidence` | Confidence: {value} | Confidence: {value} |
| `trace.reflected` | Ran a second look because confidence was below the threshold. | May pangalawang tingin dahil mababa ang confidence. |
| `trace.notReflected` | Confident enough on the first pass — no second look needed. | Sapat na ang unang tingin — hindi na kailangan ng pangalawa. |
| `trace.doubt` | Stated doubt: | Sinabing duda: |
| `trace.citedBy` | Red flags cite: | Ang mga red flag ay galing sa: |
| `trace.citedNone` | No red flag cited a knowledge-base entry. | Walang red flag na may pinanggalingang entry. |
| `trace.advise` | Advise | Payo |
| `trace.adviseDetail` | Wrote the explanation and next steps. Hotlines were looked up by name, never generated. | Isinulat ang paliwanag at mga susunod na hakbang. Ang mga hotline ay hinanap sa listahan, hindi ginawa-gawa. |
| `trace.contactsFrom` | Contacts looked up: | Mga contact na hinanap: |
| `trace.privacyNote` | Only the redacted message reaches the AI. The original is never saved or logged. | Ang na-redact na mensahe lang ang umaabot sa AI. Hindi sine-save o nilo-log ang orihinal. |

**Copy notes — read before writing the Tagalog:**
- Register is plain Filipino/Taglish as spoken, per `DESIGN.md`. Technical words that Filipinos say in English stay in English: `AI`, `confidence`, `knowledge base`, `red flag`, `link`, `account`. Do not reach for `panganib`/`pagpapatunay`-register Tagalog.
- The stage names are translated because they are headings a caregiver reads, not code identifiers.
- **`trace.privacyNote` is worded precisely and must not be "loosened".** The raw text *does* leave the browser — redaction happens server-side in `preprocess.py`. What is true is that only redacted text reaches the model and nothing raw is stored or logged. Do not write "never leaves your device".

**Steps:**
- [ ] Add `RetrievedChunk` and the three `AnalyzeResponse` fields to `api.ts`.
- [ ] Add all 24 keys to `en`, then to `tl`. `npm run build` fails if `tl` is incomplete — that is the check.

**Verification:**
```bash
cd frontend && npx tsc -b && npm test
```

**Commit:** `feat: add pipeline trace copy and response types`

---

### Task 3: Build the `PipelineTrace` component

Copy the shape of `AnalysedMessage.tsx` — a `<details>` with a bold `<summary>`, `rounded-xl border-2 border-line bg-white`. Four numbered stage blocks inside.

**Files:**
- Create: `frontend/src/components/PipelineTrace.tsx`
- Create: `frontend/src/components/PipelineTrace.test.tsx`

**Interface:**

```tsx
interface Props {
  result: AnalyzeResponse
  language: Language
}

export function PipelineTrace({ result, language }: Props)
```

Taking the whole response rather than eleven props is deliberate: the panel is a view onto one analysis, and a prop list that long is a refactor waiting to happen.

**Required `data-testid` attributes** — the E2E specs in Task 5 depend on these exact names:

| Element | testid |
|---|---|
| The `<details>` | `pipeline-trace` |
| Each stage block | `trace-stage` (four of them) |
| The confidence value | `trace-confidence` |
| The stated-doubt line | `trace-doubt` |
| The retrieved-chunk list | `trace-chunks` |

**Content per stage:**

1. **Preprocess** — badge `trace.noLlm`. `trace.type` with `message_type`; `trace.removed` with `redactions.join(' · ')`, or `trace.removedNone` when empty.
2. **Retrieve** — badge `trace.llm`. `trace.concepts` then `concepts_en` as chips, or `trace.conceptsNone` when the array is empty. Then `trace.matched` with `retrieved.length`, then the chunk IDs from `retrieved` with their `parent_type`.
3. **Detect** — badge `trace.llm`. Verdict, then `trace.confidence` with the value formatted to two decimals. Then `trace.reflected` or `trace.notReflected` from the `reflected` boolean. Then `trace.doubt` plus `low_confidence_reason` **only when it is non-null**. Then `trace.citedBy` with the distinct non-null `chunk_id`s from `red_flags`, or `trace.citedNone`.
4. **Advise** — badge `trace.llm`. `trace.contactsFrom` with the organisation names from `contacts`. Then `trace.adviseDetail`.

Close the panel with `trace.privacyNote` in `text-ink-soft`.

**Styling constraints, all load-bearing:**
- `<summary>`: `min-h-11 cursor-pointer content-center font-bold text-shield-deep` — matches `AnalysedMessage` and satisfies the 44px tap target.
- Chunk IDs and concepts must carry `break-words` (or live in a `overflow-x-auto` container). They are long unbroken strings and the a11y spec asserts no horizontal scroll at 320px **and** at 200% zoom. This is the most likely way this task fails review.
- Body text stays ≥18px — do not shrink the trace to `text-sm` to fit more in. Use `text-base` and `text-ink-soft` for secondary lines.
- No new colours. Everything comes from the `@theme` tokens in `index.css`.

**Component test — assert behaviour, not markup:**
- [ ] Renders four stages.
- [ ] Shows the concepts and the chunk IDs it was given.
- [ ] Shows `trace.notReflected` when `reflected` is false, `trace.reflected` when true.
- [ ] Renders no doubt line when `low_confidence_reason` is null, and renders it when present.
- [ ] Falls back to `trace.conceptsNone` on an empty `concepts_en`.
- [ ] Renders both languages.

**Verification:**
```bash
cd frontend && npm test
```

**Commit:** `feat: add PipelineTrace component`

---

### Task 4: Render it on the result screen

**Files:**
- Modify: `frontend/src/App.tsx`

Place it in the existing `<div className="space-y-3">` block, **after** `AnalysedMessage`. That block is the "details for whoever wants them" cluster; the trace belongs at the bottom of it, below the verdict, the reasons, and the actions. It must never sit above `NextSteps`.

```tsx
            <AnalysedMessage … />
            <PipelineTrace result={result} language={language} />
```

**Steps:**
- [ ] Import and render.
- [ ] Confirm by hand at 390px that the closed panel adds one line and does not push the reset button off a phone screen.

**Verification:**
```bash
cd frontend && npm run dev
```
Open `localhost:5173`, submit the prefilled demo message against a running backend, open the panel, read all four stages.

**Commit:** `feat: show the pipeline trace on the result screen`

---

### Task 5: Fixtures and E2E

The four fixtures are stubbed responses and are now missing three fields, so the panel will render empty against every existing spec. Fix them first.

**Files:**
- Modify: `qa/cypress/fixtures/verdict-scam.json`, `verdict-likely-scam.json`, `verdict-unclear.json`, `verdict-likely-legit.json`
- Create: `qa/cypress/e2e/analyse/pipeline-trace.cy.ts`
- Modify: `qa/cypress/e2e/analyse/verdict-variants.cy.ts`

**Fixture additions.** Give each one plausible values that match its verdict — do not paste the same block into all four. `verdict-unclear.json` in particular should carry a non-null `low_confidence_reason` and `reflected: true` (it already has `reflected: true`), because it is the fixture that exercises the doubt line. `verdict-likely-legit.json` should carry an empty `red_flags` array and therefore exercise `trace.citedNone`.

```json
  "concepts_en": ["impersonates GCash", "account lock threat", "urgency deadline", "shortened link"],
  "retrieved": [
    { "chunk_id": "msg00412", "parent_type": "message_example", "scam_type": "bank-impersonation" },
    { "chunk_id": "lure-account-suspended", "parent_type": "lure_pattern", "scam_type": "bank-impersonation" },
    { "chunk_id": "gcash-fraud-advisory-1", "parent_type": "advisory", "scam_type": null }
  ],
  "low_confidence_reason": null
```

**New spec `pipeline-trace.cy.ts` — one file for this feature, per the testing convention.** Cover:
- [ ] The panel is present on a result and is **closed** by default (`should('not.have.attr', 'open')`).
- [ ] Opening it reveals four stages.
- [ ] The concepts from the fixture are visible after opening.
- [ ] Every `chunk_id` in the fixture's `retrieved` array is visible after opening.
- [ ] `verdict-unclear.json` shows the stated-doubt line; `verdict-scam.json` does not.
- [ ] The panel renders in both languages (use `cy.setLanguage('en')` before analysing).
- [ ] **Privacy:** submit a message containing `483920` against a fixture whose `redacted_text` has it as `[OTP]`, open the panel, and assert `[data-testid="result"]` does not contain `483920`. The trace must not become the one place raw input leaks.

**Rescope the confidence assertion in `verdict-variants.cy.ts`.** The existing test asserts `[data-testid="result"]` never contains the confidence value. The trace panel lives inside `[data-testid="result"]`, so that test will now fail — correctly, because the rule changed.

Replace it with two assertions that encode the *new* rule:

```ts
      it('never displays the model confidence outside the trace panel', () => {
        cy.fixture(fixture).then((res) => {
          const shown = [`${Math.round(res.confidence * 100)}%`, String(res.confidence)]
          shown.forEach((value) => {
            cy.get('[data-testid="verdict"]').should('not.contain.text', value)
            cy.get('[data-testid="next-steps"]').should('not.contain.text', value)
            cy.get('[data-testid="uncertainty"]').should('not.contain.text', value)
          })
        })
      })

      it('keeps the confidence behind a deliberate click', () => {
        cy.get('[data-testid="trace-confidence"]').should('not.be.visible')
        cy.get('[data-testid="pipeline-trace"] summary').click()
        cy.get('[data-testid="trace-confidence"]').should('be.visible')
      })
```

Do not simply delete the original test. The rule it protected still holds for the primary result area, and deleting it would silently drop the guardrail.

**A11y.** `accessibility.cy.ts` already asserts no horizontal scroll at 320px and at 200% zoom, but only against the *input* screen. Add one case that opens the trace panel on a result at 320px and re-asserts. Chunk IDs are the overflow risk and nothing currently catches them.

**Verification:**
```bash
cd qa && npm run e2e
```
All specs green — expect 60+ tests across 9 specs.

**Commit:** `test: cover the pipeline trace panel end to end`

---

### Task 6: Documentation

Per `CLAUDE.md` § Keeping the docs true, this change touches a component, user-facing strings, the API contract, and test coverage — so it lands in three docs. **Record the reasoning, not just the outcome.**

**Files:**
- Modify: `docs/DESIGN.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `qa/TEST-PLAN.md`

**`docs/DESIGN.md`:**
- [ ] Add a `PipelineTrace` row to the § Components table (after `AnalysedMessage`), describing it as a collapsed `<details>` showing what each of the four stages did, closed by default, for the caregiver rather than the elderly user.
- [ ] Add every `trace.*` key to the § Copy table with both languages.
- [ ] **Add a short subsection recording the confidence deviation.** It must say: the primary result area still never shows a confidence number and that rule is unchanged; the trace panel does show it, because the reason for hiding it — an uncalibrated number confusing a stressed reader — does not apply behind a deliberate click, and because the number is what makes the Detect stage legible to a caregiver or an evaluator. Name the test that now enforces the narrower rule.
- [ ] Note that `low_confidence_reason` is displayed verbatim and **its language is not guaranteed** — `detect.md` specifies the output language for red-flag labels and details, but is silent on this field. Tightening the prompt is deliberately out of scope here because prompt edits require a full eval re-run. Record it as a known rough edge.

**`docs/ARCHITECTURE.md`:**
- [ ] Update the `POST /api/analyze` response example (§ API, around line 240) to include `concepts_en`, `retrieved`, and `low_confidence_reason`.
- [ ] One line noting the response carries retrieval provenance so the UI can render the trace, and that chunk *text* is deliberately not duplicated there because `similar_scams` already carries it.

**`qa/TEST-PLAN.md`:**
- [ ] Add `pipeline-trace.cy.ts` to the coverage map.
- [ ] Note the rescoped confidence assertion and why, so nobody "restores" the old broader test.

**Verification:** re-read each edited section top to bottom. A doc that contradicts the code is worse than no doc.

**Commit:** `docs: record the pipeline trace panel and the confidence deviation`

---

## Out of scope — do not do these

- **Server-side request logging.** A structured log line per analysis (verdict, confidence, chunk IDs, latency, never the text) is a reasonable separate change. It is not this one, and it needs its own decision about where logs live on the VM.
- **Editing any prompt.** Including tightening `detect.md` so `low_confidence_reason` has a guaranteed language. Prompt edits require a full eval run.
- **Showing chunk text in the trace.** `similar_scams` already does this for the three message examples.
- **Making the panel open by default**, or surfacing any of it on the primary result area.
- **A "copy trace" or export button.** Ask first; it is a plausible demo aid but it is scope the plan did not authorise.

## Definition of done

- [ ] `cd backend && uv run pytest` — green
- [ ] `cd frontend && npm test && npm run build` — green
- [ ] `cd qa && npm run e2e` — green
- [ ] Manual: submit the prefilled demo message, open the panel, and read all four stages in both languages
- [ ] Manual: at 320px with the panel open, no horizontal scroll
- [ ] Three docs updated in the same branch as the code
- [ ] Six commits, conventional prefixes, no `Co-Authored-By` trailers

## Open question for the reviewer

The trace shows `parent_type` per chunk (`message_example`, `advisory`, `lure_pattern`, `brand_rebuttal`) but the raw IDs are opaque — `msg00412` means nothing to a panelist. Options were: leave the IDs raw (chosen, because it is honest and cheap), or add a human label per chunk to the response. If the demo audience finds the IDs useless, adding a `label` field to `RetrievedChunk` is a small follow-up — but it needs a decision about what the label *is* for a message example, which has no title.
