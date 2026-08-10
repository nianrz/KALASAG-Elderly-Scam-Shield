---
title: "Slide 6 (Knowledge Base) — built artefact summary"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
updated: 2026-08-06
tags: [capstone, elderly-scam-shield, knowledge-base, deck, rag]
---

# Slide 6 — Knowledge Base

**From:** Nian · **For:** James + Lui (deck), Aki (questions slide)
**Every figure below is from `knowledge-base/out/build_report.json`, built
2026-08-06 with all 8 integrity gates passing.** Nothing here is rounded or
remembered.

---

## Headline

**The knowledge base exists.** It is one SQL database — seven tables, 2,340
rows — built by a script that runs end to end and is gated by automated
integrity checks. It was **sized from measured threat data, not from an assumed
taxonomy**: every pattern, brand, and contact in it is there because the corpus
or an official advisory put it there.

---

## What is in it

| Table | Rows | What it is |
|---|---|---|
| `sources` | 10 | Every origin, with URL, retrieval date, licence, attribution |
| `brand_rebuttals` | 4 | Each brand's own "we never ask…" statement, verbatim |
| `lure_patterns` | 10 | The recurring lure shapes, with bilingual trigger phrases |
| `reporting_contacts` | 4 | Where a victim actually reports, in priority order |
| `advisories` | 9 | Full fetched advisory text from brands and government |
| `message_examples` | 1,571 | The de-duplicated corpus, labelled and tagged |
| `kb_chunks` | 609 | The retrieval surface, with bilingual keyword fields |

**Updated 2026-08-10:** `kb_chunks` was 715 when this was written. Near-duplicate
deduplication removed 106 redundant retrieval targets — 52 template families, each
now keeping its longest member. **Use 609 on the slide.**

**27 curated documents** against the spec's ~25–30 estimate.

**Brand rebuttals — all four target brands sourced:** GCash, BDO, UnionBank,
Maya. Each row carries that brand's own words and its official hotline, taken
verbatim from a page we actually fetched. BPI (1 message in the corpus) and
Metrobank (0) are deliberately excluded despite the June scope naming them.

**Reporting contacts** lead with **I-ARC 1326**, the joint DICT/CICC/NPC/NTC
hotline — one number that covers all online scams regardless of brand.

---

## How it is sourced

Every entry carries a source URL, a retrieval date, and a licence. That is
enforced, not promised: `verify_kb.py` fails the build if any served row cites
a source without a retrieval date. `ATTRIBUTION.md` is **generated from the
database** on every build, so the licence text and the data cannot drift apart.

The corpus is CC BY 4.0 (Scott Lee Chua, PH Spam and Marketing SMS) —
attribution is a licence obligation, and we meet it mechanically.

**The provenance rule:** nothing is written from memory. A brand whose
statement we could not fetch gets no row. An invented quote attributed to a
bank is the worst thing this knowledge base could contain.

---

## The eval-leakage finding

*Worth its own line on the slide — this is the methodological care an
evaluator notices.*

The eval CSV truncates message text at 400 characters. Five of the 55 eval rows
sit at exactly that limit, and each is a **prefix** of a longer message in the
corpus — so an exact-hash holdout would have matched none of them and **leaked
all five into the retrieval pool**, quietly inflating our own evaluation.

Exact-or-prefix matching catches them: **140 raw corpus rows held out to
protect 55 eval rows** (131 exact matches, 9 prefix-only), collapsing to 53
after de-duplication. The database enforces it structurally — a `CHECK`
constraint makes it impossible for a held-out or LEGIT row to be marked
retrievable, so a future query that forgets to filter cannot reintroduce the
leak.

**692 messages are retrievable.** The 844 hard negatives are stored for
evaluation and never served.

---

## What is deliberately absent

**Embeddings.** All 609 chunks have `embedding = NULL`. This is a decision, not
an omission: the embedding provider is unresolved and the Bedrock sandbox model
list is unconfirmed, and picking a model would silently fix a vector dimension
across the schema. The stub, the placeholder dimension, and the exact steps to
fill it are documented in `HANDOFF-allen.md`.

---

## Honest gaps

State these before a mentor finds them.

- **BSP failed to fetch.** `bsp.gov.ph` served a genuine "Website is undergoing
  maintenance" notice on every attempt across three rounds. The source and the
  BSP consumer contact it backed were both **removed** rather than ship a
  hotline no fetched page supports. `content/fetch_log.json` records every
  attempt, including the failures.
- **Five sources needed browser automation.** GCash, UnionBank, BDO, PNP-ACG
  and NTC sit behind Cloudflare and return 403 to scripted requests. They are
  marked `ok-browser` and will not reproduce from `fetch_sources.py` alone.
- **The scam-type keyword lists are a reconstruction.** The lists behind the
  2026-07-29 figures were never recorded, so the computed counts differ from
  them. Brands: measured GCash 34 / BDO 30 / UnionBank 27 / Maya 6, against
  July's 39 / 29 / 24 / 9. **One conclusion changes — BDO, not UnionBank, is
  the measured #2 brand**, though the more interesting finding survives: a
  top-3 brand (UnionBank) was missing from the June scope entirely.
- **193 of 727 scam messages match no pattern list at all** (27%). Real
  coverage gap, reported rather than hidden.
- **Leakage detection is exact-or-prefix only.** Near-duplicates that are
  neither will slip through, and this corpus is heavily templated.

---

## Mentor-facing note on ruling 8

The ruling was one table per source. That became **one row per source in a
`sources` registry**, with every other table carrying a `source_id` foreign
key.

Provenance is fully intact — you can still trace any single row back to its
origin, licence, and retrieval date — but retrieval hits **one** table instead
of unioning twelve, and adding a thirteenth source is a row insert rather than
a schema migration. This is the ruling's intent (nothing unattributed) met by
its normalised form.
