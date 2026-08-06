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
| `qa/TEST-PLAN.md` | Test strategy, coverage map, what is deliberately untested |
| `docs/capstone-elderly-scam-shield.md` | Canonical proposal (source of truth for scope) |
| `docs/2026-07-29-capstone-mentor-consultation.md` | Mentor rulings — do not contradict these without saying so |

## Keeping the docs true

**A decision that only exists in code or in a chat log does not exist.** When you change something the docs describe, update the doc in the same commit as the change. A stale doc is worse than no doc — someone will act on it.

Use this map. If a change touches the left column, the right column changes with it.

| What changed | Update |
|---|---|
| Scope, a requirement, a limitation, a success criterion | `docs/PRD.md` |
| Graph shape, state fields, a node's job, the API contract, a module boundary | `docs/ARCHITECTURE.md` |
| A screen, component, accessibility rule, verdict treatment, or any user-facing string | `docs/DESIGN.md` |
| Test strategy, tooling, or coverage | `qa/TEST-PLAN.md` |
| A new build step, or a task's scope | `docs/TASKS.md` |
| A convention, invariant, tool, or ownership boundary | `CLAUDE.md` (this file) |
| Anything a teammate must install or run | `README.md` |

Two rules on top of the map:

1. **Record the reasoning, not just the outcome.** "We chose X" is half a decision. "We chose X because Y, and rejected Z because W" is the part that stops the team relitigating it next week — and it is what the mentor and the panel will ask about.
2. **Contradicting a mentor ruling is allowed; doing it silently is not.** The rulings in `docs/2026-07-29-capstone-mentor-consultation.md` are the record. If we deviate, write down the deviation and the defence, the way the KB spec does for ruling 8.

## Directory ownership

Work in your own directory. Merge to `main` daily.

Branch as `<type>/<what-changed>` — `feat/provider-switch`, `fix/redaction-otp`, `docs/test-plan`. Same type prefixes as the commit convention below. **No owner names and no task numbers in branch names**: the branch says what the change is, and the owner is already in `git log` and the table above.

| Path | Owner |
|---|---|
| `backend/` | Aki (Lead), Allen (Tech) |
| `frontend/` | James (UX) |
| `qa/` | Aki (QA) — E2E, test plan, fixtures |
| `knowledge-base/` | Nian (Domain) — **incoming subtree, do not author here** |
| `docs/` | Lui (Scribe) |

`knowledge-base/` is Nian's deliverable and arrives from his machine. Read `knowledge-base/out/kb.sqlite`; never edit its contents. Until it lands, the backend runs against `backend/tests/fixtures/kb_fixture.sqlite`.

## Stack

- **Backend** — Python 3.14, `uv`, FastAPI, LangGraph, SQLite, `sentence-transformers`
- **Frontend** — Vite + React + TypeScript + Tailwind v4
- **Tests** — pytest (backend) · Vitest (frontend components) · Cypress (E2E, in `qa/`)

Use `uv` for every Python dependency operation. Never `pip install`.

## Testing

Three layers, three homes. Tests live next to what they test, except E2E.

| Layer | Tool | Location | Runs against |
|---|---|---|---|
| Backend unit | pytest | `backend/tests/` | Fixture KB, fake LLM |
| Frontend component | Vitest | `frontend/src/**/*.test.tsx` | jsdom |
| E2E | Cypress | `qa/cypress/e2e/` | Stubbed API |
| E2E smoke | Cypress | `qa/cypress/e2e/smoke/` | **Live backend + real LLM** |

**One spec file per feature.** Not one file per layer. `verdict-scam.cy.ts`, `toggle.cy.ts`, `redaction.cy.ts` — a spec should be findable by the feature it covers, and a failing spec should name the broken feature in its filename.

**E2E is stubbed by default.** A real analysis is 3–4 LLM calls at ~20s and real money. `cy.intercept` with fixture responses covers all four verdicts and every error state, fast and deterministically. The single live spec in `smoke/` is excluded from `npm run cy:run` and exists to catch frontend/API contract drift — the one thing stubs structurally cannot see. Run it before the demo, not on every save.

**Component tests are colocated deliberately.** Tests in a distant folder stop being updated when their source changes.

Vitest is used rather than Jest because the frontend is Vite: it reads `vite.config.ts` directly, where Jest would need babel or ts-jest, ESM workarounds, and `moduleNameMapper` for CSS imports. The test-authoring API is Jest's (`describe`, `it`, `expect`, `@testing-library/jest-dom`); only `jest.fn()` becomes `vi.fn()`.

## LLM provider — read before touching `backend/app/llm.py`

The model is swappable by env var. All model access goes through `llm.py`; no other module imports a provider SDK.

```
SHIELD_MODEL=google_genai:gemini-2.5-flash   # default — free tier
SHIELD_MODEL=google_genai:gemini-2.5-flash-lite  # free tier, cheapest quota
SHIELD_MODEL=google_genai:gemini-2.5-pro     # NOT on the free tier — quota is 0
SHIELD_MODEL=bedrock_converse:...            # Accenture sandbox
```

**This project pays for no LLM API.** We run on free tiers and the Accenture Bedrock sandbox. Do not add a paid provider key or a dependency that assumes one.

Gemini Flash is the default because the key is free, needs no card, and the Bedrock sandbox model list is still unconfirmed (open question 2 in the PRD). Bedrock may itself serve Claude models under `anthropic.claude-*` IDs — that is AWS billing on the sandbox, not a key we buy, and it is fine.

**Never pass sampling parameters — no `temperature`, `top_p`, `top_k`.** Behaviour is steered by the prompt. This is a provider-portability rule, not a per-model quirk: what each provider accepts differs, some reject these outright, and a parameter that works on one `SHIELD_MODEL` and 400s on another defeats the whole point of the switch. Passing none of them works everywhere.

**`max_tokens` may bound reasoning as well as visible output**, depending on the model. Leave headroom or responses truncate mid-answer.

**Free tiers rate-limit hard.** A full eval run is roughly 200 calls; Gemini's free tier is on the order of 10–15 requests per minute. `llm.py` owns retry-with-backoff on 429 — no caller should implement its own.

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
