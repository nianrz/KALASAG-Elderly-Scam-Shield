# Handoff: knowledge base → retrieval layer

**For:** Allen
**From:** Nian
**Date:** 2026-08-06
**Build:** `knowledge-base/out/build_report.json`

Everything below is measured from the current build. If you rebuild and a
number moves, trust the report over this file and tell me.

---

## 1. What exists

`knowledge-base/out/kb.sqlite` — seven tables, built by `scripts/build_kb.py`
and gated by `scripts/verify_kb.py` (8/8 checks passing, exit 0).

| Table | Rows | Purpose |
|---|---|---|
| `sources` | 10 | Every origin: URL, retrieval date, licence, attribution. Everything else references it. |
| `brand_rebuttals` | 4 | GCash, BDO, UnionBank, Maya — each brand's own "we never ask…" statement verbatim, its official hotline, and its official channels. |
| `lure_patterns` | 10 | Recurring lure shapes with measured share/count and bilingual trigger phrases. |
| `reporting_contacts` | 4 | Where a victim reports, in priority order. I-ARC 1326 is priority 1. |
| `advisories` | 9 | Full fetched advisory text from brands and government bodies. |
| `message_examples` | 1,571 | De-duplicated corpus, labelled SCAM/LEGIT, tagged with scam type, brand, URL presence, and Taglish marker count. |
| `kb_chunks` | 609 | The retrieval surface. Everything above flattened into text + `keywords_en` / `keywords_tl`. `embedding` is NULL on every row. |

Of `message_examples`: 727 SCAM, 844 LEGIT. **569 are retrievable** — SCAM-labelled
rows that are not held out for the eval set, not fragments under 20 characters, and
not near-duplicate variants of another retrievable message. The 844 hard negatives
are stored for evaluation and are never served. See `README.md` for the filter
breakdown.

Chunk breakdown: 692 message examples, 26 advisory chunks, 10 lure patterns,
4 brand rebuttals.

---

## 2. Loading into Supabase

```bash
psql "$SUPABASE_DB_URL" -f knowledge-base/out/kb_seed.postgres.sql
```

The file is the Postgres schema followed by an INSERT per row. It begins with
`CREATE EXTENSION IF NOT EXISTS vector;` — **that must succeed first**. On
Supabase, enable pgvector from the dashboard (Database → Extensions → `vector`)
before running the seed, or the `kb_chunks.embedding vector(1536)` column will
fail to create.

There is deliberately **no vector index** (HNSW or IVFFlat) in the schema. The
right choice depends on the embedding dimension and row count, which is your
call once you pick a provider.

---

## 3. The two access patterns — and why one of them is not semantic

**This is the most important section in this file.**

The RAG Agent should search `kb_chunks` semantically. That is what it is for:
finding the lure pattern and the advisory text that explain *why* a message
looks like a scam. Approximate matching is appropriate there — a slightly
off-target explanation is still a useful explanation.

**The Advisor must fetch `brand_rebuttals` and `reporting_contacts` by primary
key.** `brand_id` and `contact_id` are exact lookups. Never similarity search,
never a nearest-neighbour fallback, never "closest brand."

The reason is concrete: these tables contain phone numbers. If a user asks
about a GCash message and a fuzzy match returns BDO's row, an elderly person
gets handed `(+632) 8888-0000` as "the number to call about your GCash
problem." That is a direct harm, produced by the system, to the exact person
the system exists to protect. A vector search has no notion of being wrong
about which bank it is.

If the brand tag is unknown, the correct behaviour is to return **no** brand
rebuttal and fall back to `reporting_contacts` priority 1 (I-ARC 1326), which
covers all online scams regardless of brand. Returning nothing is always
better than returning the wrong hotline.

---

## 4. Setting the embedding dimension

Two places must change together, to the same number:

1. `knowledge-base/kb/db.py` → `EMBEDDING_DIM = 1536`
2. `knowledge-base/schema/001_schema.postgres.sql` → `embedding vector(1536)`

1536 is a **placeholder**, not a recommendation. Set both to your chosen
model's dimension, then implement `embed_batch(texts) -> list[list[float]]` in
`knowledge-base/scripts/embed.py` and run it. Right now it reports
"609 chunks awaiting embeddings" and exits 0 without doing anything, which is
the intended state.

---

## 5. Decisions that are yours

- **Embedding model and provider.** Unresolved. The Accenture Bedrock sandbox
  model list is unconfirmed — verify what is actually available before
  committing.
- **Chunk overlap.** Currently zero. `split_advisory()` splits on paragraph
  boundaries at 2,000 chars, hard-splitting oversized paragraphs. Add overlap
  there if retrieval quality needs it.
- **Similarity threshold and top-k.** Not set anywhere.
- **Cross-lingual mitigations 1 and 2.** Mitigation 3 (bilingual keyword fields
  on every chunk) is already applied at curation time — it had to be, since it
  cannot be added at runtime. Whether to also use a multilingual embedding
  model (1) and/or extract English concepts before retrieval (2) is open. The
  corpus is Taglish; the advisories are English. This gap is real, not
  theoretical.

---

## 6. Known limitations, stated plainly

- **The scam-type and brand keyword lists are a reconstruction.** The lists
  behind the 2026-07-29 analysis were never recorded, so `kb/tagging.py`'s
  counts differ from the figures in the older team documents (GCash 39 /
  UnionBank 29 / BDO 24 / Maya 9 → now GCash 34 / BDO 30 / UnionBank 27 /
  Maya 6). **BDO, not UnionBank, is the measured #2 brand.** The rule is to
  report computed counts, never to tune the lists until they reproduce old
  numbers. `brand_rebuttals.measured_frequency` reconciles exactly with
  `SELECT brand_tag, COUNT(*) FROM message_examples WHERE label='SCAM' GROUP BY 1`.
- **193 of 727 SCAM rows are `unclassified`** — no keyword list matched them.
  That is a real coverage gap, reported rather than hidden.
- **`lure_patterns.measured_share` / `measured_count` do not reconcile with the
  tagger.** Those columns carry the 2026-07-29 hand-analysis figures (e.g.
  casino 465, 56.2%); `classify_scam_type` on the same 827-message spam corpus
  computes casino 481 (58.2%) and bank-impersonation 76 (9.2%). Unlike
  `brand_rebuttals.measured_frequency`, which I recomputed so it matches
  `message_examples` exactly, the lure-pattern figures were left as authored.
  If you surface them next to tagger-derived counts, they will visibly
  disagree. Recomputing them is a small change to `content/lure_patterns.yaml`
  if you want that consistency — flagging rather than silently changing curated
  numbers.
- **Eval leakage detection is exact-or-prefix only.** Near-duplicates that are
  neither will slip through, and this corpus is heavily templated, so assume
  some remain. All 55 eval rows are matched and held out; 692 retrievable rows
  are clean under that rule.
- **Any brand that could not be sourced has no row.** BPI (1 message) and
  Metrobank (0) are excluded despite the June scope naming them.
- **Any source that failed to fetch is absent.** BSP is the one casualty:
  `bsp.gov.ph` served a genuine maintenance notice on every attempt across
  three rounds, so the source and the BSP consumer contact it backed were both
  removed rather than serve a hotline no fetched page supports.
  `content/fetch_log.json` records every attempt, including the failures and
  the five sources that needed browser automation because Cloudflare 403s
  scripted requests.
- **GCash's rebuttal and hotline come from two different GCash pages.** The
  Help Center article carries the statement but no number; the number is from
  the gcash.com footer, fetched the same day. `sources.yaml` says so.

---

## 7. Do not hand-edit `ATTRIBUTION.md`

It is generated from the `sources` table on every `build_kb.py` run and will be
overwritten. The corpus is CC BY 4.0 — attribution is a licence obligation, not
a courtesy. If attribution text needs to change, change it in
`content/sources.yaml` and rebuild.
