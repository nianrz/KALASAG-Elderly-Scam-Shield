# Elderly Scam Shield — Knowledge Base

The retrieval layer for the Elderly Scam Shield capstone: a SQLite database
(plus a Postgres/Supabase seed) of Philippine scam evidence and official
counter-guidance, built reproducibly from a public SMS corpus and advisories
fetched from the organisations that published them.

Two components consume it:

- **The RAG Agent** searches `kb_chunks` semantically to ground its explanation
  of *why* a message looks like a scam.
- **The Advisor** reads `brand_rebuttals` and `reporting_contacts` **by primary
  key**, never by similarity. A fuzzily-matched hotline handed to an elderly
  user is a direct harm, so those two tables are looked up exactly or not at
  all. See `HANDOFF-allen.md`.

## The seven tables

| Table | Rows | What it holds |
|---|---|---|
| `sources` | 10 | Every origin, with URL, retrieval date, licence, and attribution. |
| `brand_rebuttals` | 4 | Each impersonated brand's own "we never ask…" statement, verbatim, plus its official hotline and channels. |
| `lure_patterns` | 10 | The recurring lure shapes, with measured share/count and bilingual trigger phrases. |
| `reporting_contacts` | 4 | Where a victim actually reports, in priority order (I-ARC 1326 first). |
| `advisories` | 9 | Full fetched advisory text from brands and government bodies. |
| `message_examples` | 1,571 | The de-duplicated corpus, labelled SCAM/LEGIT and tagged. |
| `kb_chunks` | 715 | The retrieval surface: everything above, flattened, with bilingual keyword fields. Embeddings are **not** populated. |

## Rebuilding from scratch

```bash
python3 -m venv knowledge-base/.venv
knowledge-base/.venv/bin/pip install -r knowledge-base/requirements.txt

# Optional: re-fetch the live advisory pages (rewrites content/advisories/
# and content/fetch_log.json). Several sources need a real browser and will
# not reproduce from a script — see "Fetch reality" below.
knowledge-base/.venv/bin/python knowledge-base/scripts/fetch_sources.py

knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
knowledge-base/.venv/bin/python knowledge-base/scripts/verify_kb.py
```

`build_kb.py` downloads the corpus, validates the curated content, writes
`out/kb.sqlite`, `out/kb_seed.postgres.sql`, `out/build_report.json`, and
regenerates `ATTRIBUTION.md`. `verify_kb.py` must exit 0 — the build is not
done until it does.

Tests: `knowledge-base/.venv/bin/python -m pytest knowledge-base/tests` (50 tests).

## Current build figures

From `out/build_report.json`, 2026-08-07:

- **Corpus reconciliation:** `ok: true`, every delta 0 — 8,255 messages total,
  1,907 with usable text after the author's privacy redaction (933 ads, 827
  spam, 144 gov, 3 notifs).
- **Eval holdout:** all 85 eval rows matched; 88 rows held out after
  de-duplication and whitespace-variant matching; **675 retrievable messages**.
  Only SCAM-labelled, non-held-out rows over 20 characters are retrievable —
  the 844 hard negatives are stored but never served.
- **Curated documents:** 27.
- **Scam types (of 727 SCAM rows):** casino 420, bank-impersonation 70, prize 22,
  loan 10, package 8, crypto 2, job-task 2, unclassified 193.
- **Brands impersonated (SCAM rows):** GCash 34, BDO 30, UnionBank 27, Maya 6,
  BPI 1. `brand_rebuttals.measured_frequency` reconciles with these exactly.
- **Fetches:** 4 ok by script, 5 ok via browser, 1 failed (BSP — see below).

### Why 88 held out and not 140

De-duplication runs first: 1,907 usable rows collapse to 1,571 distinct
normalised texts, and the held-out rows collapse along with them. Both numbers
are correct at their own stage.

### Holdout matches an identity key, not display text

Matching runs over an alphanumeric-only key — lowercase, everything else
stripped, Cyrillic kept because scam domains use homoglyphs. The previous rule
collapsed runs of whitespace but did not remove it, so `msg01484` (`Sumali ka
na! w1903b.xyz`) was neither equal to nor a prefix of `msg01483` (`Sumali ka
na!w1903b.xyz`), which is eval row M010. It stayed `retrievable = 1`: the
Detector could retrieve the answer to its own test case. The key change caught
it and `msg00780` with no regressions across the corpus, and
`backend/tests/test_holdout.py` now asserts the invariant in the unit suite.

### Fragments are not retrievable

Rows under 20 characters — `"Hello"`, `"Hi po"`, `"getcash!!"`, `"001204649"` —
are labelled SCAM upstream but carry no pattern to match, so they are excluded
from retrieval regardless of label. `verify_kb.py` gates this.

### Gold labels are inherited, and not clean

Labels come from the upstream Kaggle corpus and were not re-derived. In the one
26-message slice checked by hand during the 2026-08-07 eval rebalance, 10 were
unusable: `msg01066` ("You will no longer receive marketing SMS from BPI") is a
legitimate opt-out confirmation labelled SCAM, `msg00638` is a legitimate
roaming welcome labelled SCAM, and six are fragments too short to carry a label.

The 85 eval messages are hand-reviewed. **The rest of the corpus is not**, and
nothing here should be read as claiming otherwise. Say so in the paper rather
than presenting inherited labels as verified ground truth.

### The click-this-link prevalence claim was wrong

`lure_patterns.click-this-link` stated that two-thirds of scam messages carry no
link at all. Measured against the corpus in this same database, it is 26 of 692
unheld SCAM rows — **3.8%**, off by a factor of about 17. The figure was
presumably external and never checked against the corpus. The advice it framed
("a link is a strong signal, but its absence proves nothing") is correct
independently and survives; the prevalence claim has been replaced with what the
link-free scams actually are, which is chat-bait moving the victim to Messenger
or Telegram.

### Why the counts differ from the 2026-07-29 figures

The July hand-analysis reported GCash 39 / UnionBank 29 / BDO 24 / Maya 9.
The keyword lists behind those figures were never recorded, so `kb/tagging.py`
is a reconstruction and its counts differ. The rule is to **report computed
counts and never tune the lists to reproduce old numbers**. One conclusion
changes: BDO, not UnionBank, is the measured #2 impersonated brand.

## Fetch reality

`content/fetch_log.json` records every fetch attempt and its outcome, including
the failures. Several PH sites (GCash Help Center, UnionBank, PNP-ACG, NTC)
sit behind Cloudflare and return 403 to scripted requests; they were captured
with browser automation and are marked `ok-browser`. Those will **not**
reproduce from `fetch_sources.py` alone.

BSP is absent entirely: `bsp.gov.ph` has served a genuine "Website is undergoing
maintenance" notice on every attempt, so the source and the BSP consumer
contact it backed were both removed rather than ship an unverifiable hotline.
`verify_kb.py` enforces this — no served row may cite an undated source.

## Why there are no embeddings

The embedding provider is unresolved, and picking one is not this deliverable's
call. `kb_chunks.embedding` is `NULL` for all 715 rows and `scripts/embed.py`
is a documented stub. `EMBEDDING_DIM` in `kb/db.py` and `vector(1536)` in
`schema/001_schema.postgres.sql` are placeholders that must both change to the
chosen model's dimension. See `HANDOFF-allen.md`.

## Provenance rule

Every rebuttal quote, hotline, and advisory body in this repository is verbatim
from a page that was actually fetched, with the date recorded. Nothing is
written from memory. A brand or agency whose statement could not be sourced
gets no row — an invented quote attributed to a bank is the worst failure this
knowledge base could contain.

`ATTRIBUTION.md` is generated from the `sources` table on every build. Do not
edit it by hand.
