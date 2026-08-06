# Test Plan — Kalasag

**Owner:** Aki (QA) · Companion to `docs/PRD.md` and `docs/DESIGN.md`

## What we are actually protecting

This is not a CRUD app where a bug means a bad row. The failure modes that matter are specific:

1. **A hallucinated hotline number.** A wrong number handed to a panicking elderly user is a direct harm and the failure this product cannot survive. Tested by asserting the rendered contact matches the API response byte for byte.
2. **A scam link rendered as clickable.** Making the malicious URL tappable inside the tool that just flagged it would be worse than not having the tool.
3. **A false sense of safety.** Any path that lets the UI imply "this is definitely safe" — a green `LIKELY_LEGIT`, a missing uncertainty line — is a correctness bug.
4. **A leaked OTP.** Redacted values must never round-trip to the screen or the logs.
5. **A hung reflection loop.** The only place the system can fail to terminate.

Every one of these has a named test. Coverage percentage is not a goal; these five are.

## Layers

| Layer | Tool | Location | Runs against | When |
|---|---|---|---|---|
| Backend unit | pytest | `backend/tests/` | Fixture KB, `FakeListChatModel` | Every commit |
| Frontend component | Vitest | `frontend/src/**/*.test.tsx` | jsdom | Every commit |
| E2E | Cypress | `qa/cypress/e2e/` | Stubbed API | Every commit |
| E2E smoke | Cypress | `qa/cypress/e2e/smoke/` | Live backend + real LLM | Before a demo, and after any API change |

### Why E2E is stubbed by default

A real analysis is three to four LLM calls at roughly twenty seconds and real money. A fully live suite would be slow, billable, nondeterministic, and dependent on provider rate limits — which in practice means it stops being run by midweek. Stubbing with `cy.intercept` covers all four verdicts and every error state in under a minute, for free, with identical results every run.

The cost of stubbing is that nothing proves the frontend and backend agree on the response shape. That is precisely what `smoke/live-pipeline.cy.ts` exists for, and why it asserts the contract from `ARCHITECTURE.md § API` explicitly rather than just checking that a verdict appears.

### Why component tests are colocated

A test in a distant folder stops getting updated when its source changes. `VerdictCard.test.tsx` next to `VerdictCard.tsx` is a test that gets maintained.

### Why Vitest rather than Jest

The frontend is Vite. Vitest reads `vite.config.ts` directly; Jest would need babel or ts-jest, ESM workarounds, and `moduleNameMapper` for CSS imports — real setup cost for no gain in a one-week build. The test-authoring API is Jest's, so nothing about writing these tests is Jest-specific except `vi.fn()` in place of `jest.fn()`.

## Spec map

One file per feature. A failing spec names the broken feature in its filename.

| Spec | Feature | Key assertions |
|---|---|---|
| `analyse/verdict-scam.cy.ts` | The SCAM path | Verdict leads; icon + word, not colour alone; steps precede explanation; uncertainty line present; **no clickable link from the message** |
| `analyse/verdict-variants.cy.ts` | All four verdicts | Distinct headline each; uncertainty line on every one; **`LIKELY_LEGIT` is not green**; the model's confidence value never renders (the static "100%" in the uncertainty copy is DESIGN.md wording, not a confidence readout) |
| `analyse/next-steps.cy.ts` | Steps and contacts | Ordered list; **hotline matches the API byte for byte**; official numbers are `tel:` links |
| `analyse/red-flags.cy.ts` | Flags and collapsibles | Label + detail per flag; sections collapsed by default; empty sections omitted, not shown empty; no fabricated filler flag |
| `language/toggle.cy.ts` | EN/TL toggle | Segmented control not dropdown; copy switches; `<html lang>` follows; language reaches the API; persists across reload |
| `privacy/redaction.cy.ts` | PII handling | Privacy note before submit; **redacted value never rendered back**; freshness date shown |
| `errors/error-states.cy.ts` | Failure paths | Empty submit; network failure; **no stack trace or submitted text in errors**; long-input warning not silent truncation; KB-unavailable still shows a verdict |
| `a11y/accessibility.cy.ts` | `DESIGN.md` rules | 18px body; 44px tap targets; keyboard-only run; visible focus; no h-scroll at 320px or 200% zoom; verdict announced via `role="status"` |
| `smoke/live-pipeline.cy.ts` | Contract | Real analysis returns SCAM/LIKELY_SCAM; **response has every documented key**; confidence within 0–1 |

## Running

```bash
cd qa
npm run e2e          # stubbed suite, starts the frontend automatically
npm run cy:open      # interactive runner, for writing and debugging specs
npm run e2e:smoke    # live — needs the backend on :8000 and a provider key
```

Backend and component suites:

```bash
cd backend  && uv run pytest
cd frontend && npm test
```

## Test data

Fixtures in `qa/cypress/fixtures/` mirror the response contract in `ARCHITECTURE.md § API`. **When that contract changes, these change in the same commit** — a fixture that has drifted from the API is a test that passes while the product is broken, which is worse than no test.

The 55-message gold set (`eval-set-candidate-55.csv`) is *not* E2E test data. It is the model evaluation set, consumed by `backend/eval/run_eval.py`, and it is held out of the knowledge base so the Detector cannot retrieve the answers to its own test.

## Deliberately not tested

Stated so nobody assumes coverage that does not exist.

- **Model output quality.** Whether a verdict is *correct* is measured statistically by `eval/run_eval.py` over 55 labelled messages, not asserted per-case. An LLM assertion in a Cypress spec would be flaky by construction.
- **Tagalog register.** Whether output reads as plain Taglish rather than textbook Tagalog is judged by a native speaker (criterion S6). No automated proxy for this is worth trusting.
- **Cross-browser.** Cypress runs Electron only. The demo is on one machine.
- **Load and concurrency.** Single-user local demo.
- **Visual regression.** No baseline screenshots; the UI is still moving.
- **The knowledge base build.** Nian's `verify_kb.py` gates that, including the eval-leakage check. We consume the KB, we do not test its construction.

## Known gaps

- Specs are written against the `data-testid` contract in `DESIGN.md` and **will fail until the UI is built** (tasks T5 and T14). This is intentional — the specs are the acceptance criteria for those tasks.
- Near-duplicate scam messages that are neither identical nor prefixes of eval-set entries stay retrievable, so the eval slightly overstates accuracy. Documented in `PRD.md § Limitations`.
- The confidence threshold is calibrated on the same 55 messages the accuracy is reported on. That is fitting to the test set and is stated as such on the deck.
