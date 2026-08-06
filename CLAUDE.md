# Kalasag — Elderly Scam Shield

STSP001 capstone. A web app where an elderly Filipino or their caregiver pastes a suspicious SMS, email, or URL and gets **verdict → explanation → next steps** in plain Filipino/Taglish or English, produced by a LangGraph pipeline over a curated Philippine scam knowledge base.

**Presentation is one week out.** Scope decisions favour a working local demo over polish. Do not add features that were not asked for.

## The name

**Renamed to Kalasag on 2026-08-06.** In the UI the product is just **Kalasag**; `Kalasag — Elderly Scam Shield` is the full form for doc titles and the deck.

**The env vars were renamed with it.** `SHIELD_*` was a product-name prefix, so it pointed at a name that no longer exists. The replacements are named for what they configure rather than for the app:

| Was | Now |
|---|---|
| `SHIELD_MODEL` | `LLM_MODEL` |
| `SHIELD_MAX_TOKENS` | `LLM_MAX_TOKENS` |
| `SHIELD_RETRY_BACKOFF` | `LLM_RETRY_BACKOFF` |
| `SHIELD_CONFIDENCE_THRESHOLD` | `CONFIDENCE_THRESHOLD` |
| `SHIELD_KB_PATH` | `KB_PATH` |

The last two are unprefixed on purpose — the confidence threshold gates the graph's reflection edge and `KB_PATH` points at a SQLite file, so neither is an LLM setting and `LLM_KB_PATH` would have been a category error.

**Update your `backend/.env` by hand.** A leftover `SHIELD_*` var does not error — pydantic-settings just doesn't see it and uses the default, so the app runs happily on the wrong model. Nothing in the logs will look wrong.

Still unchanged: the `scam-shield-backend` and `qa` package names, which are internal and cost a lockfile churn to move.

Docs dated before 2026-08-06 — the mentor consultation note, the canonical proposal, `docs/superpowers/**` — still say "Elderly Scam Shield". That is the record of what the project was called then, not a stale doc. Do not rewrite them.

## Docs

| File | What it settles |
|---|---|
| `docs/GUIDE.md` | Orientation — the whole system end to end, plus the redeploy loop. Companion, not authority: if it disagrees with a doc below, that doc wins and the guide is stale |
| `docs/PRD.md` | Scope, users, requirements, success criteria |
| `docs/ARCHITECTURE.md` | Graph shape, state, API contract, module boundaries |
| `docs/DESIGN.md` | UI/UX spec, accessibility rules, EN/TL copy |
| `docs/TASKS.md` | Ordered build tasks with verification steps |
| `docs/DEPLOYMENT.md` | DLSU VM runbook — first-time install, redeploy, tmux, teardown |
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
LLM_MODEL=bedrock_converse:global.anthropic.claude-sonnet-5   # default — Accenture sandbox, verified live
```

**This project pays for no LLM API.** The Accenture Bedrock sandbox serves Claude models under `anthropic.claude-*` IDs on AWS billing — not a key we buy. Do not add a paid provider key or a dependency that assumes one.

**Gemini support was removed on 2026-08-06.** It existed because the Bedrock sandbox model list was unconfirmed; once the sandbox was verified live on Claude Sonnet 5, the free-tier key was deleted and `langchain-google-genai` dropped. The provider switch itself is unchanged — re-adding any provider is an `uv add` of its langchain package plus an `LLM_MODEL` string. (Historical: Gemini's free tier granted zero quota on `gemini-2.5-pro`, found in T1.)

**The sandbox region gotcha:** ap-southeast-1 does not serve Claude Sonnet 5 in-region — only the **global inference profile** works, hence the `global.` prefix in the model ID. The bare `anthropic.claude-sonnet-5` ID fails from Singapore. Auth is a bearer token in `AWS_BEARER_TOKEN_BEDROCK` — the `_BEDROCK` suffix is load-bearing; botocore silently falls back to SigV4 without it.

**Never pass sampling parameters — no `temperature`, `top_p`, `top_k`.** Behaviour is steered by the prompt. This is a provider-portability rule, not a per-model quirk: what each provider accepts differs, some reject these outright, and a parameter that works on one `LLM_MODEL` and 400s on another defeats the whole point of the switch. Passing none of them works everywhere.

**`max_tokens` may bound reasoning as well as visible output**, depending on the model. Leave headroom or responses truncate mid-answer.

**A full eval run is roughly 200 calls.** `llm.py` owns retry-with-backoff on 429 — no caller should implement its own. The sandbox's rate limits are undocumented; the retry loop is what absorbs whatever they turn out to be.

**Embeddings are not the chat provider.** Retrieval uses a local `sentence-transformers` model with a fixed 384 dimension. Switching `LLM_MODEL` must never require re-embedding the KB.

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

## "Upload this to the VM" — the redeploy runbook

**Trigger this section on any of:** "upload this to our VM", "deploy this", "push it to the VM", "redeploy", "update the VM", "ship it", or any phrasing that means *the code on `main` should now be running at `altdsidccf.dlsu.edu.ph:32050`*. Do not ask which procedure to use — this is the only one.

Full explanation in `docs/GUIDE.md` §11; first-time install in `docs/DEPLOYMENT.md`.

### What this is

The VM has **no clone of the repo and never will**. Three files the app cannot run without are gitignored and would not survive a `git pull` on the VM: `knowledge-base/out/kb.sqlite`, `backend/.env`, and the `backend/static/` build. So the transport is **one ~1 MB tarball built on the Mac**, not git.

### Preflight

Check and report, do not silently proceed:

1. On `main`, clean tree, up to date with origin. If the user's work is on a branch or uncommitted, say so and stop — deploying is not the moment to discover unmerged work.
2. `backend/.env` exists and has a non-empty `AWS_BEARER_TOKEN_BEDROCK`.
3. `knowledge-base/out/kb.sqlite` exists (~1.7 MB).
4. `cd backend && uv run pytest` passes. A red suite is a stop, not a warning.

### Steps you run (Mac side)

```bash
cd /Users/achibukz/Code/GitHub/Elderly-Scam-Shield
git checkout main && git pull

cd frontend && npm run build && cd ..
rm -rf backend/static && cp -R frontend/dist backend/static

COPYFILE_DISABLE=1 tar czf ~/Desktop/kalasag-deploy.tgz \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.venv' \
  --exclude='backend/eval/results' \
  backend/app backend/tests backend/eval backend/pyproject.toml backend/uv.lock \
  backend/.env backend/.env.example backend/static backend/check_bedrock_connection.py \
  knowledge-base/out/kb.sqlite docs/DEPLOYMENT.md
```

**`npm run build` is not optional, even for a backend-only change.** The archive ships `backend/static/` wholesale, so skipping it re-deploys whatever UI was in that folder last time.

**The tar paths are relative to the repo root and must stay that way.** `config.py` resolves the KB as `<backend>/../knowledge-base/out/kb.sqlite`; flattening the structure sends it silently back to the fixture KB and nothing looks wrong.

Then confirm the archive is roughly 1 MB. Much larger means an exclude did not fire and a `.venv` or `node_modules` is inside.

### Steps you hand to the user (VM side)

Both need the VM password, so you cannot run them. Print them and tell the user to run each with the `! ` prefix:

```bash
scp -P 32051 ~/Desktop/kalasag-deploy.tgz root@altdsidccf.dlsu.edu.ph:/root/
```

Then in the tmux session on the VM:

```bash
tar xzf /root/kalasag-deploy.tgz -C /root/kalasag && rm /root/kalasag-deploy.tgz
tmux attach -t kalasag        # Ctrl-C to stop uvicorn
source /root/kalasag/.local/env.sh
cd /root/kalasag/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 80
# detach: Ctrl-b then d — or, if VS Code eats Ctrl-b, `tmux detach -s kalasag` from a second terminal
```

Add `uv sync` after the `source` line **only if `pyproject.toml` or `uv.lock` changed in this deploy** — check the diff and say which. Otherwise skip it; a redeploy should cost one megabyte, not a re-download of torch.

`source /root/kalasag/.local/env.sh` is never optional. A fresh tmux shell has never seen those exports and `uv` is not on `PATH` without them.

### Verify — you run these

```bash
curl -s http://altdsidccf.dlsu.edu.ph:32050/api/health
curl -s http://altdsidccf.dlsu.edu.ph:32050/api/meta
```

**`chunk_count` must be 732.** Anything smaller means `KB_PATH` fell back to the fixture — the app still answers plausibly on it, so this check is the only thing that catches it.

Then tell the user to open the URL and run **one real analysis end to end**, and to hard-refresh (`Cmd-Shift-R`) first. Health and meta never touch the LLM, so nothing short of a full request proves the deploy.

### Afterwards

- Tell the user to delete `~/Desktop/kalasag-deploy.tgz` — it contains the Bedrock bearer token in cleartext.
- Extract-over-the-top overwrites and adds but never deletes. If this deploy **renamed or removed** a backend source file, say so and recommend `rm -rf /root/kalasag/backend/app` before extracting.

## Conventions

- Match surrounding style. No comments unless the *why* is non-obvious.
- Every feature gets unit tests. Keep them passing.
- Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- No `Co-Authored-By` trailers.
