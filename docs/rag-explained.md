---
title: "How RAG works in Kalasag — and how to measure it"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Aki (QA)
updated: 2026-08-08
tags: [capstone, kalasag, rag, retrieval, embeddings, measurement, orientation]
---

# How RAG works in Kalasag — and how to measure it

**Companion to** `docs/GUIDE.md` (whole-system orientation) and `docs/2026-08-08-kb-rag-measurement-review.md` (the measurement findings). This one explains the retrieval mechanism itself: what it does, why it works, and why measuring it needs more than one number.

Figures are from the KB built 2026-08-10 (609 chunks, after near-duplicate deduplication). If `build_report.json` says something else, it is newer and it wins.

Deduplication on 2026-08-10 removed 106 redundant retrieval targets. The metrics in "Measuring it" below were re-run on both pools that day, so they are a true before/after rather than a single snapshot.

---

## Nothing in RAG "knows" anything

Retrieval-augmented generation sounds like the system understands your question and goes and finds the answer. It doesn't. It converts text into coordinates and measures distance. That's the whole mechanism — everything else is engineering around that one idea.

### Text becomes coordinates

`intfloat/multilingual-e5-small` turns any string into **384 numbers** — a point in 384-dimensional space. It is trained so text with similar *meaning* lands in a similar direction, regardless of wording or language.

> "Naka-hold ang account mo" and "your account has been suspended" share no words, but point nearly the same way.

That cross-language property is why a multilingual model was chosen. A monolingual English embedder would put the Taglish version somewhere unrelated.

### Distance becomes a dot product

Vectors are stored normalized (`normalize_embeddings=True` in `backend/app/retrieval/embedder.py`), so every point sits on a unit sphere. Cosine similarity then reduces to a plain dot product — no division, no magnitude bookkeeping.

The entire search is one line, `backend/app/retrieval/store.py:94`:

```python
scores = (query_vectors @ self._vectors.T).max(axis=0)
```

A `(n_queries × 384) @ (384 × 609)` matrix multiply, then take the top 6. Full scan, no vector index — at 609 rows numpy brute force beats any tree, and an index would be a dependency and a build step for nothing.

### The prefix asymmetry is load-bearing

e5 models are trained with `"query: "` on the search side and `"passage: "` on the stored side. `embedder.py` keeps them separate:

```python
def embed_queries(texts):  return _model().encode([f"query: {t}"   for t in texts], normalize_embeddings=True)
def embed_passages(texts): return _model().encode([f"passage: {t}" for t in texts], normalize_embeddings=True)
```

Dropping the prefixes, or using the same one on both sides, measurably degrades retrieval. It looks like decoration. It isn't.

---

## What is actually in the KB

609 chunks, and they are not all the same kind of thing:

| parent type | count | what it is |
|---|---|---|
| `message_example` | 569 | real corpus scam messages |
| `advisory` | 26 | official warnings |
| `lure_pattern` | 10 | named tactics with red flags |
| `brand_rebuttal` | 4 | "BDO will never text you a link" |

Only chunks whose parent is a retrievable message survive the load query in `store.py`. LEGIT rows, eval holdouts, and fragments are excluded **at load**, not at query time — so no search can return them even by accident. That is how pipeline invariant 5 is enforced structurally rather than by remembering to filter.

---

## How it knows what to fetch

This is the part specific to Kalasag, and it is the real answer.

**The KB is English. Users write Taglish.** Embedding "Nanalo ka ng ₱50,000, i-claim mo dito" straight against English chunks leans on the multilingual model happening to bridge the gap — embedding luck, and luck is not a design.

So the retrieve node spends an LLM call *before* searching. `backend/app/prompts/retrieve.md` asks the model to rewrite the message into 3–6 short English **red-flag concepts describing tactics, not surface words**:

```
["unexpected prize win", "urgency deadline", "claims account suspended"]
```

Then it searches with the concepts **and** the original text together — `backend/app/graph/nodes/retrieve.py:35`:

```python
chunks = store.search(concepts + [state["redacted_text"]], top_k=TOP_K)
```

Two different jobs:

- **concepts** cross the language gap and describe the *tactic*
- **raw text** catches surface matches a paraphrase would lose — a specific brand, a domain, a phone number

### Why `.max(axis=0)` and not a mean

Each query — every concept, plus the raw text — **votes independently**, and each chunk keeps its single best score across all of them.

Averaging would punish specialists. A chunk that matches "shortened link" perfectly but has nothing to do with the other four concepts would get dragged toward the middle and lose to a chunk that is vaguely related to everything. Max keeps the sharp match. In retrieval you want the best evidence for *any* angle, not the most inoffensive compromise across all of them.

---

## Two tracks, and only one is RAG

This is pipeline invariant 2, and it is the most important design decision in the retrieval layer.

| what | how it is fetched | why |
|---|---|---|
| evidence chunks | vector similarity, top 6 | fuzzy is fine — it is context for the Detector to weigh |
| hotlines, official URLs | `SELECT … WHERE brand_id = ?` | fuzzy is catastrophic |

`backend/app/retrieval/contacts.py` opens with *"No similarity search, ever."* A semantically-retrieved hotline is about 90% right, and for a phone number handed to a frightened person, 90% right is wrong. Those come back by primary key and are passed to the Advisor as data to reproduce verbatim.

**Only the evidence path is RAG.** If someone proposes "just retrieve the hotline too, it's in the KB anyway" — that is the one failure this product cannot survive.

---

## Why use RAG at all

The model does not reliably know that `9910.омск.рус` is a Philippine casino lure, or what BDO's current advisory actually says. Retrieval grounds the verdict in curated local specifics the model never saw in training.

The alternatives are worse for this project: fine-tuning costs money and a labelled dataset and has to be redone per model, and stuffing the whole KB into every prompt costs tokens on 609 chunks to use 6. RAG is updateable by editing a YAML and rebuilding — which matters when the domain expert is a teammate, not an ML engineer.

---

## Measuring it

### The core problem

**End-to-end verdict F1 cannot see retrieval.** Two completely different situations produce the same output:

1. Retrieval fetched garbage → the Detector guessed right from the message text alone
2. Retrieval fetched perfect evidence → the Detector used it

Both score as a win. So a good F1 is not evidence the KB is doing anything. You have to measure the stages separately, and then measure whether the stage *contributes*.

### Retrieval-level metrics — zero LLM calls

These are pure geometry. They run in seconds and cost nothing, so they can go in CI. Both pools measured 2026-08-10 under identical conditions:

| question | metric | before (715) | after (609) |
|---|---|---|---|
| Is it cheating? | eval messages reachable by search | 0 (was 13 pre-rebuild) | **0** |
| Does it fetch six *different* things? | distinct messages in top-6, mean / worst | 5.376 / 2 | **6.000 / 6** |
| Did it fetch the right *kind* of thing? | `scam_type` recall@3 / @6 / @10 | 0.800 / 0.800 / 0.829 | **0.800 / 0.829 / 0.857** |
| Did it fetch anything? | queries returning 0 chunks | 0 of 85 | **0 of 85** |
| Do the vectors separate the classes? | mean top-6 similarity, SCAM vs LEGIT | 0.887 vs 0.853 | separation 0.0310 |

Three readings worth carrying forward:

**The `recall@3 == recall@6` plateau was duplication, and it is gone.** Chunks 4–6 used to contribute no additional same-type evidence, which made `TOP_K = 6` look like wasted context. The cause was that slots 4–6 held template variants of slots 1–3, and a variant cannot add a new `scam_type`. With 106 redundant targets removed, recall@6 pulls ahead of recall@3 (0.829 vs 0.800). **`TOP_K` stays at 6** — cutting to 3 would now cost 0.029 recall. The earlier "investigate 6 → 3" recommendation is superseded.

**Every query now returns six distinct messages.** The mean went 5.376 → 6.000 and the worst case 2 → 6, so no query has a duplicate pair in its window any more. The rarer curated content picked up the freed slots: `advisory` appearances went 11 → 12 and `lure_pattern` 1 → 2 over the 85 queries.

**Recall is measured against a skewed pool.** Deduplication narrowed the skew without removing it: `casino` went from 406 of 675 retrievable (60%) to 356 of 569 (63%), and unclassified from 177 to 134.

### The ablation — the only test of contribution

Run the eval twice: retrieval enabled, then retrieval returning empty. Compare F1.

If the number does not move, the KB is decoration and the Detector is working from message text alone. There is no cheaper substitute for this measurement, and it is the question a panelist is most likely to ask. Cost is 2× a full run (~680 calls).

### Baselines — every metric needs a floor

A score with no control is not evidence. Two trivial rules, both zero LLM calls:

| baseline | score | status |
|---|---|---|
| `has_link → SCAM` | F1 **0.660** | reported in every eval run |
| top-6 similarity threshold | accuracy **0.824** (0.835 pre-dedup) | **not reported — should be** |

The second is the real ceiling to beat. A pipeline scoring under ~0.824 accuracy is losing to a dot product with no LLM involved at all.

### The distinction to internalize

> `recall@k` asks **did it find it**. The ablation asks **did it matter**.

A system can score well on the first and zero on the second. Only the second justifies the architecture.

---

## Reading the code

Shortest path to understanding the retrieval layer, in order:

1. `backend/app/retrieval/embedder.py` — 33 lines, text → vectors
2. `backend/app/retrieval/store.py` — load-time filtering, then the one-line search
3. `backend/app/prompts/retrieve.md` — what the concept hop asks for
4. `backend/app/graph/nodes/retrieve.py` — how the two get combined
5. `backend/app/retrieval/contacts.py` — the track that is deliberately *not* RAG
