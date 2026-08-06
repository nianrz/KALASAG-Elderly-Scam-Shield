---
title: "Design — Elderly Scam Shield Knowledge Base"
type: spec
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Nian (Domain Expert)
updated: 2026-08-05
tags: [capstone, elderly-scam-shield, knowledge-base, rag, sql, spec]
---

# Design — Elderly Scam Shield Knowledge Base

**Owner:** Nian (Domain Expert) · **Consumes:** RAG Agent, Advisor Agent · **Hands off to:** Allen (Tech Lead)

This spec covers the construction of the curated Philippine scam-pattern knowledge base for the STSP001 capstone. It implements Nian's outstanding action item from the 2026-07-29 mentor consultation: *"Move the KB into a single SQL database with one table per source. Verify the Kaggle PH SMS dataset's licence and label quality."*

The second half of that action item is already complete — see [Prior work](#prior-work-this-builds-on).

## Prior work this builds on

| Source | What it settles |
|---|---|
| `2026-07-29-nian-dataset-findings.md` | Dataset verified: 8,255 messages, **1,907 usable** after redaction, CC BY 4.0, coverage to 2026-06-03. Scam composition measured. Licence and label quality **verified** — the action item's second half is done. |
| `2026-07-29-slide6-knowledge-base-rewrite.md` | KB sized at ~25–30 documents. Brands ranked by measured frequency. Four bank-impersonation lure patterns quantified. |
| `2026-07-29-plan3-scam-shield-datasets.md` | Live source list for the RAG corpus (bucket B) confirmed. |
| `2026-07-29-capstone-mentor-consultation.md` | Rulings 3, 4, 8 — RAG stays, RAG is its own agent, storage is one SQL database. |
| `eval-set-candidate-55.csv` | The 55 messages that must be **held out** of the KB. |

## Rulings this design is bound by

From the 2026-07-29 mentor consultation (Rozelle Samonte, Accenture):

1. **RAG stays** (ruling 3). Pattern-matching breaks on novel scammer scripts; RAG matches on intent.
2. **Retrieval is its own agent**, sitting between preprocessing and the Detector (ruling 4). The KB therefore feeds **detection**, not only advice.
3. **Storage is a single SQL database with the data sources as tables** (ruling 8), because a pile of CSVs forces the retrieval step to jump between files.

### Deviation from the literal reading of ruling 8

Ruling 8 is implemented as **one row per source in a `sources` registry**, not one table per source.

A literal twelve-table implementation (`src_bsp`, `src_gcash`, `src_bdo`, …) produces near-identical schemas, makes every new source a migration, and forces retrieval to UNION across a dozen tables — reproducing in SQL the exact file-jumping problem the ruling was meant to eliminate. The requirement being protected was *structured storage in one database with provenance intact*. This design meets that: every chunk carries a `source_id`, every source carries its URL, retrieval date, and licence.

**Defense if challenged:** "One table per source became one row per source in a `sources` registry. Every chunk still carries its provenance, and retrieval hits one table instead of unioning twelve."

## Objectives

1. Produce a **portable SQL seed** — schema, curated content, and a loader that builds the database from scratch on any machine, with no dependency on infrastructure the team has not yet stood up.
2. Populate it with **verbatim, citable content** from live Philippine authorities and bank/e-wallet fraud pages.
3. Include the **real message corpus** so the RAG Agent has exemplars to match intent against and the UI's "similar scams" panel has something real to show.
4. Leave every **still-open decision open** — embedding provider, retrieval strategy, cross-lingual approach — while making the cheap curation-time insurance (bilingual keywords) unconditional.

## Non-goals

- Generating embeddings. The LLM provider is unresolved (open question 2) and the Bedrock sandbox model list is unconfirmed. The schema reserves the column; `embed.py` ships as a provider-swappable stub and is not run.
- Choosing a retrieval strategy, chunk-overlap policy, or similarity threshold. Allen's call, documented in the handoff.
- Provisioning Supabase. The seed targets it; it does not require it.
- Any change to the LangGraph pipeline, agent prompts, or UI.

---

## Architecture — two consumers, two access patterns

The KB serves two agents whose needs differ, and conflating them is the primary failure this design guards against.

| Consumer | Access pattern | Reads |
|---|---|---|
| **RAG Agent** | Semantic / vector retrieval | `kb_chunks` — lure patterns, advisories, real exemplars. Returns context to the Detector. |
| **Advisor Agent** | Deterministic keyed lookup | `brand_rebuttals`, `reporting_contacts`, keyed by brand and verdict. |

### The Advisor must not retrieve semantically

Hotline numbers, official URLs, and brand rebuttal quotes are fetched by primary key, never by nearest-neighbour search.

A fuzzy-matched or hallucinated hotline number handed to a panicking elderly user is a direct harm and the one failure mode the product cannot survive. Semantic search is appropriate for "what pattern is this message like"; it is not appropriate for "what number should this person call." The schema enforces the distinction by keeping contact data in typed columns rather than in retrievable prose.

### Where the KB sits in the pipeline

```
User paste
  → Preprocessing (Python: type detect, PII redact)
  → RAG Agent ──────semantic──────► kb_chunks
  → Detector (verdict + confidence; guardrail rules in prompt)
  → [confidence < threshold → self-reflection → Detector]
  → Advisor ────────keyed lookup──► brand_rebuttals, reporting_contacts
  → Verdict → Explanation → Next steps
```

---

## Schema

Seven tables. Postgres/pgvector is the target dialect; SQLite is the local mirror used for building and verification, since neither Postgres nor Docker is available on the authoring machine.

### `sources`
Provenance registry. One row per source. This is where ruling 8 lives.

| Column | Type | Notes |
|---|---|---|
| `source_id` | text PK | e.g. `gcash-fraud-advisory`, `bsp-consumer-advisories` |
| `name` | text | Display name |
| `organisation` | text | GCash, BSP, PNP-ACG, … |
| `url` | text | Canonical URL fetched |
| `retrieved_at` | date | Fetch date. Feeds the UI freshness indicator. |
| `licence` | text | e.g. `CC BY 4.0`, `public advisory` |
| `attribution` | text | Exact attribution string required by the licence |
| `notes` | text | Fetch caveats, partial availability |

### `brand_rebuttals`
The highest-value-per-entry table. Four core brands, ranked by measured frequency in the 827-message corpus: **GCash (39) · UnionBank (29) · BDO (24) · Maya (9)**.

| Column | Type | Notes |
|---|---|---|
| `brand_id` | text PK | `gcash`, `unionbank`, `bdo`, `maya` |
| `brand_name` | text | Official display name |
| `rebuttal_quote` | text | **Verbatim.** The brand's own "we will never ask you to…" statement. |
| `official_hotline` | text | Exact number |
| `official_url` | text | Official fraud/support page |
| `official_channels` | text | App-only, in-app support, etc. |
| `measured_frequency` | integer | Count in the corpus |
| `source_id` | text FK → `sources` | |

BPI (1 message) and Metrobank (0) are **out** of the core set, reversing the June scope. Included only if fetching is trivial, and flagged `measured_frequency` 1 and 0 respectively so nobody mistakes them for priorities.

### `lure_patterns`
~10 rows. The four measured bank-impersonation patterns, plus one per remaining measured scam type so the KB can speak to what a user will actually paste.

| Column | Type | Notes |
|---|---|---|
| `pattern_id` | text PK | `verify-update-account`, `account-suspended`, … |
| `name` | text | Human-readable |
| `description` | text | What the lure does and why it works |
| `scam_type` | text | `bank-impersonation`, `casino`, `job-task`, `loan`, `package`, `prize` |
| `measured_share` | real | Share of the relevant slice |
| `measured_count` | integer | |
| `red_flags` | text | The signals that identify it |
| `triggers_en` | text | English trigger phrases |
| `triggers_tl` | text | Tagalog/Taglish trigger phrases, mined from the corpus |

Bank-impersonation patterns and their measured shares: verify/update account (34%), account suspended (24%), urgency deadline (17%), click this link (17%). Additional scam-type patterns sized from the corpus: casino/gambling (465, 56.2%), job/task (21, 2.5%), loan (16, 1.9%), package/delivery (14, 1.7%), prize/raffle (14, 1.7%).

Carrying measured frequency in the table means the KB can state **how common a pattern actually is**, not merely that it exists.

### `reporting_contacts`

| Column | Type | Notes |
|---|---|---|
| `contact_id` | text PK | `i-arc-1326`, `pnp-acg`, `bsp-consumer`, `npc`, `ntc-1682` |
| `organisation` | text | |
| `hotline` | text | |
| `email` | text | |
| `url` | text | |
| `covers` | text | What this body actually handles |
| `priority` | integer | I-ARC 1326 first — the joint DICT/CICC/NPC/NTC reporting centre |
| `source_id` | text FK → `sources` | |

### `advisories`
~10 longer-form documents, stored verbatim.

| Column | Type | Notes |
|---|---|---|
| `advisory_id` | text PK | |
| `title` | text | |
| `body` | text | **Verbatim.** No paraphrase. |
| `published_at` | date | Nullable — many advisories are undated |
| `language` | text | `en`, `tl`, `mixed` |
| `source_id` | text FK → `sources` | |

Target sources: BSP, NPC, DICT, PNP-ACG, ScamWatch Pilipinas, AMLC, cybersecurity.ph.

### `message_examples`
The real corpus. Renamed from `scam_examples` because it holds both classes — the negatives belong here, and naming the table for one class invites the wrong query.

| Column | Type | Notes |
|---|---|---|
| `message_id` | text PK | Stable ID assigned at load |
| `text` | text | Verbatim message |
| `text_hash` | text | Normalised-text SHA-256, unique. Dedupe + holdout key. |
| `label` | text | `SCAM` / `LEGIT` |
| `source_category` | text | Dataset's own label: `spam`, `ads`, `gov` |
| `scam_type` | text | Nullable — `bank-impersonation`, `casino`, … |
| `brand_tag` | text | Nullable — impersonated brand |
| `has_url` | boolean | 33% of scam messages carry one |
| `taglish_markers` | integer | Tagalog marker count; 36% carry 3+ |
| `retrievable` | boolean | See below |
| `eval_holdout` | boolean | See below |
| `source_id` | text FK → `sources` | scottleechua dataset |

Expected content: 827 scam + 933 `ads` + 144 `gov` = 1,904 rows, less duplicates and less the 55 held out.

**`retrievable` defaults to false for all `LEGIT` rows.** Hard negatives are stored — they are valuable as labelled contrast and for anyone building eval tooling — but retrieving a legitimate BDO promo into a "similar scams" panel is its own failure mode, and the flag makes the default safe rather than relying on every future query remembering to filter.

### `kb_chunks`
The single retrieval surface. Everything the RAG Agent sees, and nothing it does not.

| Column | Type | Notes |
|---|---|---|
| `chunk_id` | text PK | |
| `text` | text | The retrievable text |
| `parent_type` | text | `lure_pattern`, `advisory`, `message_example`, `brand_rebuttal` |
| `parent_id` | text | Polymorphic reference |
| `source_id` | text FK → `sources` | Provenance, always present |
| `keywords_en` | text | |
| `keywords_tl` | text | |
| `embedding` | `vector(N)` | **Unpopulated.** Dimension set when the provider is chosen. |

Chunking policy: curated entries are short enough to be one chunk each. Advisories are chunked on section boundaries, targeting ~500 tokens. Message examples are one chunk each — SMS are short by construction.

---

## Cross-lingual retrieval

Open question 3 in the canonical plan, unraised at the last consultation. The corpus is lopsided: authoritative sources are English, and 36% of scam messages carry three or more Tagalog markers — genuine Taglish, not translated English. A Taglish query therefore has to retrieve English documents.

Three mitigations were identified in the plan. Only one of them must happen **at curation time**:

| Mitigation | When it can be decided | This spec |
|---|---|---|
| 1. Multilingual embedding model | Runtime — Allen | Left open |
| 2. Detector extracts English concepts first, then retrieves | Runtime — Allen | Left open |
| 3. Hand-written EN/TL keyword fields per entry | **Curation time — now, or never cheaply** | **Implemented unconditionally** |

`keywords_en` and `keywords_tl` are populated on every chunk, with Tagalog trigger phrases mined from real messages in the corpus rather than invented. This costs curation effort now, forecloses nothing, and is the only one of the three that cannot be retrofitted without redoing the curation.

---

## Integrity constraints

These are what make the KB defensible in front of an evaluator.

### Eval holdout by text match, not by ID
The `M001`–`M055` identifiers in `eval-set-candidate-55.csv` are Nian's, assigned during sampling. They do not exist in the source dataset. Matching on them would silently fail and leak the entire eval set into the KB — the Detector would then retrieve the answers to its own test, and the eval numbers would be meaningless.

Holdout is therefore matched on **normalised text**: lowercase, collapse whitespace, strip surrounding punctuation.

**Exact matching alone is insufficient — verified 2026-08-06.** The eval CSV truncates message text at **400 characters**. Five rows hit that cap (M039, M041, M045, M049, M054), and each is a strict prefix of a longer message still present in the dataset. Under exact-hash matching all five would pass the holdout check and leak.

The rule is therefore **exact-or-prefix**: a dataset row is held out if its normalised text equals the normalised eval text, or begins with it. Measured against a fresh pull of the dataset:

| Rule | Eval rows matched | Dataset rows held out |
|---|---|---|
| Exact hash only | 50 / 55 | 131 |
| **Exact-or-prefix** | **55 / 55** | **140** |

140 rather than 55 because scam messages are templated and repeat near-verbatim across the corpus — a single eval message can correspond to several dataset rows, and every one of them has to go. Retrievable pool after holdout: **1,767** of 1,907 usable rows.

Every held-out row is loaded with `eval_holdout = true` and `retrievable = false`, so the exclusion is auditable rather than invisible.

The same normalisation catches genuine duplicates already present in the eval set — M049/M054 and M051/M053 are identical message pairs.

**Verification gate:** `verify_kb.py` fails the build if any retrievable row's normalised text equals or begins with any eval row's normalised text.

### Provenance and freshness
Every chunk resolves to a `source_id` with a `retrieved_at` date. The UI freshness indicator required by the plan reads from `MAX(retrieved_at)`. A chunk without a resolvable source is a build failure.

### Licence attribution
The scottleechua dataset is CC BY 4.0 and requires attribution. Licence and attribution are schema fields on `sources`, not a README footnote, and `ATTRIBUTION.md` is generated from the table so the two cannot drift. This matters because the plan calls for a publicly deployed demo.

### Verbatim fidelity
`rebuttal_quote` and `advisories.body` are stored exactly as published. A paraphrased bank rebuttal has none of the authority that makes it worth retrieving — the entire value of "GCash never asks you to verify your account via an SMS link" is that GCash said it.

`fetch_log.json` records what each URL actually returned, so a quote can always be traced to a fetch.

---

## Build pipeline

```
fetch_sources.py   live fetch → content/advisories/*.md (+ provenance front-matter)
                              → content/fetch_log.json
       ↓
build_kb.py        content/ + dataset → out/kb.sqlite
                                      → out/kb_seed.postgres.sql
       ↓
verify_kb.py       integrity checks; non-zero exit on failure
       ↓
embed.py           provider-swappable stub — NOT RUN
```

Each stage is independently runnable and idempotent. `fetch_sources.py` writes to disk so that a later build never depends on a site still being up; the fetched markdown is the durable artifact, and it is committed.

### Dataset acquisition
Only `eval-set-candidate-55.csv` is present locally. The source dataset is pulled from:

```
https://raw.githubusercontent.com/scottleechua/data/main/spam-and-marketing-sms/text-messages.csv
```

CC BY 4.0, public, ~924 KB. Columns: `date-received`, `date-read`, `sender`, `category`, `text`.

**Verified against a fresh pull on 2026-08-06** — every figure in the 2026-07-29 findings note reproduces exactly:

| Figure | Recorded | Fresh pull |
|---|---:|---:|
| Total messages | 8,255 | 8,255 |
| Usable text | 1,907 | 1,907 |
| spam usable | 827 | 827 |
| ads usable | 933 | 933 |
| gov usable | 144 | 144 |
| notifs usable | 3 | 3 |
| Coverage end | 2026-06-03 | 2026-06-03 09:25:34 |

**Reconciliation gate:** the build re-checks these counts and surfaces any mismatch loudly rather than accepting it silently, because these numbers appear on the deck.

### Fetch failures
Some sources will fail — pages move, NGO sites go down, PhishTank-style registration walls appear. A failed fetch is recorded in `fetch_log.json` with its error and **omitted from the KB**. It is never replaced with remembered or reconstructed content. The build prints a summary of what was and was not obtained, and the final report states the gaps plainly.

---

## Verification

`verify_kb.py` checks:

1. **No eval leakage** — no retrievable chunk hash matches an eval-set hash.
2. **Provenance complete** — every chunk has a resolvable `source_id`; every source has a `retrieved_at`.
3. **Referential integrity** — no orphaned `parent_id` in `kb_chunks`.
4. **Negatives not retrievable** — no `LEGIT` row has `retrievable = true`.
5. **Contact fields populated** — no `brand_rebuttals` row with an empty hotline or official URL. A blank contact field is worse than an absent row, because the Advisor may emit it.
6. **Count reconciliation** — corpus counts match the recorded figures, or the discrepancy is reported.
7. **Curated volume** — the count of curated documents is reported against the ~25–30 estimate on the deck.

Failures exit non-zero. The build is not "done" until this passes, and its output is quoted in the completion report rather than summarised.

---

## Deliverables

```
knowledge-base/
  README.md
  schema/
    001_schema.postgres.sql        pgvector-ready
    001_schema.sqlite.sql          local mirror
  content/
    sources.yaml
    brand_rebuttals.yaml
    lure_patterns.yaml
    reporting_contacts.yaml
    advisories/*.md                verbatim, with provenance front-matter
    fetch_log.json
  scripts/
    fetch_sources.py
    build_kb.py
    embed.py                       stub, unrun
    verify_kb.py
  out/
    kb.sqlite
    kb_seed.postgres.sql
  ATTRIBUTION.md
  HANDOFF-allen.md
```

Plus, outside `knowledge-base/`:

**Corrections to stale files.** Three known-false statements currently sit in team documents:
- The canonical topic page states the dataset's *"licence and label quality unverified"* — both were verified on 2026-07-29 (CC BY 4.0; 1,907 of 8,255 usable).
- The same page still lists the *phishing/smishing/vishing/romance/OFW/investment/package-delivery* taxonomy, which the 827-message analysis disproved — four of those seven are near-absent in SMS, and the two largest real categories are missing.
- Slide 7 line 100 claims *"No public labeled Filipino/Taglish scam dataset exists"* — false, and disprovable by a mentor in ten seconds.

**KB summary for slide 6** — what is in the KB, sized and sourced, for the deck and for next week's session with Sir JJ.

**`HANDOFF-allen.md`** — Supabase load steps, schema assumptions, where embeddings plug in, and the retrieval decisions that remain his: embedding model, chunk overlap, similarity threshold, and which of cross-lingual mitigations 1 and 2 to adopt on top of the keyword fields.

---

## Risks

| Risk | Mitigation |
|---|---|
| Bank fraud pages are JS-rendered or blocked | Record the failure in `fetch_log.json`, omit the entry, report the gap. Never substitute remembered text for a fetched quote. |
| Re-pulled dataset differs from the analysed download | Count reconciliation gate; prefer a local copy if one exists. |
| Eval leakage through truncated eval text | **Confirmed real**, not hypothetical — the eval CSV truncates at 400 chars and 5 rows hit the cap. Exact-or-prefix matching, with a verification gate. |
| Eval leakage through near-duplicates that are neither equal nor prefixes | Out of scope. The corpus is heavily templated, so near-duplicate scam messages that differ mid-string will remain retrievable. Flagged in the handoff as a known limitation of the eval, not silently absorbed. |
| `vector(N)` dimension unknown | Column declared with a placeholder dimension and a single-line change documented in the handoff. SQLite mirror stores embeddings as a BLOB. |
| Ruling-8 deviation challenged by the mentor | Documented above with a one-sentence defense. |

## Open questions this spec does not close

Carried forward from the canonical plan, unchanged:

1. Whether the Advisor merges into the Detector.
2. Which model, concretely — bake-off pending, sandbox model list unconfirmed.
3. Cross-lingual retrieval strategy at runtime (mitigations 1 and 2).
4. The English | Tagalog output toggle.
5. Screenshot/OCR input for the accidental-link-tap risk.
6. Whether a deployed demo is possible in the Accenture sandbox.

Note that **retrieval-side placement** is *not* on this list. The slide-6 note argued retrieval belongs on the Advisor side with the Detector running prompt-only; the mentor ruled the opposite on 2026-07-29 without that argument having been put to her. This spec implements the ruling. If the team wants to revisit it, that is a question for the next session, not a change to make unilaterally.
