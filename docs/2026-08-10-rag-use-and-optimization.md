---
title: "How RAG was used and optimized in Kalasag"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Nian (Domain)
updated: 2026-08-10
tags: [capstone, kalasag, rag, retrieval, optimization, presentation]
---

# How RAG was used and optimized in Kalasag

**For:** the team lead, and whoever presents the retrieval section.
**Companions:** `docs/rag-explained.md` (the mechanism, in depth) and `docs/2026-08-08-kb-rag-measurement-review.md` (the measurement findings). This document answers one narrower question — *what did we optimize, and what is the evidence* — and is deliberately explicit about which claims are measured and which are reasoned.

---

## The short answer

RAG is used to ground the Detector's verdict in a curated Philippine scam corpus: 609 chunks, searched by vector similarity, with the top 6 passed into the prompt as evidence.

**Optimization happened in the knowledge base, not in tuning the retrieval code.** The retrieval layer has two commits in its entire history (`536fbc2`, `9c88f43`) and has never been iterated against a measured result. What *was* optimized is (a) a set of design decisions made up front for stated reasons, and (b) the composition of the retrievable pool — and (b) is the part with a measured before/after.

**The one measured optimization:** 23.4% of the retrievable pool was near-duplicate template variants. Removing them (675 → 569 targets) took the average query from 5.4 distinct messages in its six retrieval slots to **6.0**, with the worst case going from 2 to 6, and raised type-correct recall@6 from **0.800 to 0.829**. Measured on 2026-08-10, both pools under identical conditions, zero LLM calls.

If someone asks "did you optimize your RAG system," the honest answer is: *yes, once, with a measurement on both sides — we found and removed 23% redundancy in the retrieval pool and retrieval measurably improved. The rest of the design was reasoned up front rather than tuned. We have not yet run the ablation that proves retrieval changes the final verdict.* Claiming more than that will not survive a follow-up question.

---

## How RAG is used

Five steps. Full mechanism in `docs/rag-explained.md`.

1. **Redact.** `preprocess.py` strips OTPs, account and card numbers, phones, and emails. Only redacted text moves forward (pipeline invariant 1). Retrieval never sees raw user input.
2. **Concept hop.** The retrieve node spends one LLM call rewriting the message into 3–6 short English red-flag *concepts* describing tactics, not surface words — `["unexpected prize win", "urgency deadline"]`. This exists because the KB is English and users write Taglish.
3. **Search.** `backend/app/graph/nodes/retrieve.py:35` searches with the concepts **and** the redacted text together. Every query votes independently; each chunk keeps its single best score (`store.py:94`). Top 6 come back.
4. **Ground.** Those 6 chunks go into the Detector prompt as evidence to weigh.
5. **Keyed lookup, separately.** Hotlines and official URLs are fetched by primary key from `brand_rebuttals` / `reporting_contacts` and handed to the Advisor as data — never retrieved semantically (pipeline invariant 2). `contacts.py:1` opens with *"No similarity search, ever."*

**Only step 3 is RAG.** Step 5 deliberately is not, and that distinction is the most important design decision in the retrieval layer: a fuzzy-matched hotline given to a frightened person is the one failure this product cannot survive.

---

## What was optimized

Three tiers, separated by how strong the evidence is. Do not present tier 1 as though it were tier 2.

### Tier 1 — design decisions, reasoned but not A/B measured

Each of these is a real choice with a real justification. None has a measured before/after in this repo.

| Decision | Why | Evidence |
|---|---|---|
| **Concept hop before searching** | Embedding Taglish straight against English chunks relies on the multilingual model happening to bridge the gap. Concepts make the bridge explicit. | Reasoned. Costs one LLM call per analysis. **Not measured against a no-concept baseline.** |
| **Multi-query: concepts *plus* raw text** | Concepts cross the language gap and describe the tactic; raw text catches surface matches a paraphrase loses — a brand, a domain, a number. | Reasoned |
| **`.max(axis=0)` rather than mean** | Averaging punishes specialists. A chunk that nails "shortened link" but is unrelated to the other concepts would lose to a chunk vaguely related to everything. Max keeps the sharp match. | Reasoned |
| **`query:` / `passage:` prefix asymmetry** | Required by how `multilingual-e5-small` was trained. Dropping the prefixes, or using one on both sides, measurably degrades retrieval. | Established property of the model, not measured here |
| **Normalized vectors, brute-force numpy scan** | Normalizing makes cosine similarity a plain dot product. At 609 rows a full scan beats any index, and an index would be a dependency and a build step for nothing. | Reasoned; correct at this scale |
| **Two-track retrieval** (vector for evidence, keyed lookup for contacts) | Fuzzy is fine for evidence the Detector weighs; catastrophic for a phone number reproduced verbatim. | Invariant 2 |
| **Load-time exclusion, not query-time filtering** | Non-retrievable rows never enter the store, so no query can return them even by accident. Invariant 5 is enforced structurally rather than by remembering to filter. | `store.py`, `_EXCLUDE_NON_RETRIEVABLE` |

### Tier 2 — knowledge-base curation, measured

This is the tier with real numbers, and it is where the actual optimization work landed.

**The retrievable pool is curated, not just dumped in.** Of 1,571 corpus messages, only 569 are retrievable:

| filter | rows removed | why |
|---|---|---|
| LEGIT-labelled rows excluded | 844 | the KB is evidence of *scams*; legit messages are not evidence |
| eval-set messages held out | 88 | invariant 5 — retrieving the test means measuring nothing |
| **fragments under 20 chars dropped** | **6** | `"Hello"`, `"Hi po"`, `"getcash!!"`, `"001204649"` — labelled SCAM upstream but carrying no pattern to match. As retrieval targets they are pure noise. |
| **near-duplicate templates collapsed** | **106** | 52 template families — 14 near-identical "earn 500P watching YouTube" messages, 9 `[ BANCO DE ORO ]` variants. Each family keeps its longest member. |

That leaves **569 message examples**, plus 26 advisories, 10 lure patterns, and 4 brand rebuttals — **609 chunks**.

Two of these filters are genuine retrieval-quality optimizations, both enforced by gates in `verify_kb.py`:

The **fragment filter** (`build_kb.py:43`, `MIN_RETRIEVABLE_LEN = 20`) removes chunks that could win a top-6 slot on a short query while contributing nothing. Small (6 rows) but real.

The **near-duplicate filter** (`kb/dedupe.py`) is the larger one, and it has a measured problem behind it. Clustering the retrievable pool by Jaccard similarity over character shingles found that **23.4% of it — 158 of 675 messages — sat inside a near-duplicate cluster**, 106 rows redundant across 52 families. Exact deduplication never caught them because they differ by an amount, a domain, or a greeting. Left in, several of the six chunks the Detector sees are variants of one message: six slots, two or three distinct pieces of evidence. Each family now keeps its longest member, since that carries the most detail a query could match.

This is the one change in the project with a before/after: **675 → 569 retrieval targets, 715 → 609 chunks, 106 redundant targets removed.**

**Holdout matching was hardened** so the eval set cannot leak into the pool. Matching moved from normalised display text to an aggressive identity key that survives whitespace and punctuation drift — `msg01484` differed from its eval twin by a single space and stayed retrievable under the old rule. Verified against the current build: **88 holdouts, 0 leaks, 0 false collisions.** This is correctness, not performance, but it is what makes every other number trustworthy.

**Retrieval-level metrics now exist** (they did not before 2026-08-08), all zero-LLM-cost. Both pools were measured on 2026-08-10 under identical conditions — same model, same queries, same scoring — so this is a true before/after:

| question | metric | before (715) | after (609) | |
|---|---|---|---|---|
| Does it fetch six *different* things? | distinct messages in top-6, mean | 5.376 | **6.000** | ✓ |
| | distinct messages in top-6, worst case | 2 | **6** | ✓ |
| Does it fetch the right *kind*? | `scam_type` recall@3 | 0.800 | 0.800 | = |
| | `scam_type` recall@6 | 0.800 | **0.829** | ✓ |
| | `scam_type` recall@10 | 0.829 | **0.857** | ✓ |
| Does it fetch anything at all? | queries returning 0 chunks, of 85 | 0 | 0 | = |
| Is the eval set leaking? | eval messages reachable by search | 0 | 0 | = |
| Do the vectors separate the classes? | similarity separation SCAM−LEGIT | 0.0336 | 0.0310 | ✗ |
| | accuracy from similarity alone | 0.835 | 0.824 | ↓ |

**The redundancy was real and is now gone.** Before, the average query got 5.4 genuinely different messages in its six slots and the worst got **two** — four of six were copies of each other. After deduplication all 85 queries return six distinct messages, and the *minimum* is six, so no query has a single duplicate pair left.

**The one number that fell is not retrieval getting worse.** Duplicates inflated the scores of scam queries — a scam matching six copies of itself scores uniformly high — so removing them removes some of that inflation. Recall went up while separation dipped. The practical effect is that the trivial dot-product baseline the pipeline must beat is now slightly *lower* (0.824, not 0.835), which is mildly in our favour.

Caveat to state before anyone quotes recall@k: the pool is skewed, and dedup narrowed but did not remove the skew — the retrievable pool went from 406 `casino` of 675 (60%) to **356 of 569 (63%)**, and unclassified rows from 177 to 134. Deduplication removed proportionally more casino variants than anything else, which is expected: template families are what casino spam is made of.

**Method, and what it does not show.** Both pools were reconstructed from the same `kb.sqlite` and embedded with the production model (`intfloat/multilingual-e5-small`, `query:`/`passage:` prefixes, normalized vectors, `score = (queries @ vectors.T).max(axis=0)`). The harness reproduces the 2026-08-08 figures on the old pool exactly — recall 0.800 / 0.800 / 0.829, separation 0.0336, similarity accuracy 0.835, parent-type appearances 85 / 11 / 1 / 1 — which is the evidence that the comparison is sound and not a re-implementation artefact. It searches with the **raw eval text as a single query**, matching Aki's method; the real pipeline searches with the LLM-extracted concepts *plus* the raw text, so these are not production absolutes. The direction of the change is what this establishes.

### Tier 3 — resolved: `TOP_K` stays at 6

**The 2026-08-08 review recommended investigating `TOP_K` 6 → 3, on the evidence that `recall@3 == recall@6` (both 0.800). Do not act on that recommendation — it was true of the old pool only.**

The plateau was caused by the duplication. Slots 4–6 held template variants of what slots 1–3 already returned, and a variant cannot contribute a new `scam_type`. With the 106 redundant targets removed, `recall@6` pulls ahead of `recall@3` — 0.829 against 0.800 — so cutting the window to 3 would now *lose* 0.029 recall. `TOP_K = 6` (`retrieve.py:15`) is earning its context tokens.

The rarer curated content benefited too: over the 85 queries, `advisory` appearances went 11 → 12 and `lure_pattern` 1 → 2. Small, but it is the curated chunks reclaiming slots that duplicates were occupying — and it removes the worry that shrinking the window would starve the advisory path.

If asked "what would you optimize next," this is the answer to give: *we measured that 23% of the retrievable pool was near-duplicate templates, removed them, and re-measured — every query now returns six distinct pieces of evidence instead of an average of 5.4, and type-correct recall at six rose from 0.800 to 0.829. That also invalidated our own earlier plan to shrink the retrieval window, which we dropped.*

---

## What has not been measured

**Whether retrieval contributes to the final verdict.** This is the gap, and it should be stated before a panelist finds it.

End-to-end verdict F1 structurally cannot see retrieval. Two different situations produce the same score: retrieval fetched garbage and the Detector guessed right from the message text alone, or retrieval fetched perfect evidence and the Detector used it. Both look like a win.

The test that separates them is the **ablation** — run the 85-message eval twice, once with retrieval enabled and once with it returning empty context, and compare F1. If the number does not move, the KB is decoration. There is no cheaper substitute. Cost is roughly 680 LLM calls, about two full eval runs.

It needs a `--no-retrieval` flag in `run_eval.py` that makes the retrieve node return `{"concepts_en": [], "retrieved": []}` without the LLM hop. That flag does not exist yet.

**A second gap worth knowing before the panel does:** thresholding on raw top-6 similarity alone, with zero LLM calls, reaches **0.824 accuracy** on the current pool (0.835 before deduplication). The eval currently reports a `has_link → SCAM` control at F1 0.660. Similarity is the stronger trivial baseline and it is not reported anywhere. If the full pipeline scores below ~0.824 accuracy, it loses to a dot product — and that is exactly the question a panelist asks.

---

## How to answer the question in the room

A three-sentence version that is true:

> We use retrieval to ground the verdict in a curated Philippine scam corpus rather than in what the model happens to remember. The optimization we can defend with numbers is the retrieval pool: we measured that 23% of it was near-duplicate template variants — the same scam re-sent with one detail changed — so the Detector's six retrieved chunks often carried only two or three distinct pieces of evidence. Removing them took the average query from 5.4 distinct messages to 6.0 and raised type-correct recall from 0.800 to 0.829, and it also invalidated our own earlier plan to shrink the retrieval window, which we dropped.

Then, if pressed on what is *not* proven:

> That is a retrieval-level measurement. It shows the KB fetches better evidence; it does not yet show the final verdict changes, because end-to-end F1 cannot distinguish good retrieval from a lucky guess off the message text. The ablation that closes that question is our next run.

Do not quote a **verdict** accuracy improvement — that has not been measured. The defensible claims are the retrieval numbers above, and they are strong enough on their own.

---

## Cheapest path to a stronger claim before the presentation

In priority order:

1. ~~Re-run the retrieval metrics on the 609-chunk pool.~~ **Done 2026-08-10** — results in tier 2 above.
2. **Add the similarity baseline to `run_eval.py`** alongside `baseline_confusion`. Zero marginal LLM cost, and it removes the worst surprise a panelist could spring. Use **0.824**, the post-dedup figure. Pin it in `backend/tests/test_eval.py` the way 0.660 is pinned.
3. **Run the ablation** (~680 calls). The only measurement that turns "the KB fetches better evidence" into "the KB changes the answer." Needs a `--no-retrieval` flag in `run_eval.py` first.
4. ~~Decide `TOP_K`.~~ **Resolved** — stays at 6; see tier 3.
5. **Document the KB rebuild step** in `qa/TEST-PLAN.md` and the deploy preflight in `CLAUDE.md`. Not a RAG optimization, but a fresh checkout currently gets a red suite and a silently stale artifact.

Item 2 is cheap. Item 3 is the one that changes what we can claim.

---

## Reproducing the before/after

Zero LLM calls. Needs `sentence-transformers` and `numpy`, which the knowledge-base venv
does not carry — make a throwaway venv rather than adding them to `requirements.txt`:

```bash
python3 -m venv /tmp/measure-venv
/tmp/measure-venv/bin/pip install sentence-transformers
/tmp/measure-venv/bin/python measure.py
```

Both pools are reconstructed from the same `kb.sqlite`, so the comparison needs no second
database: `OLD` is every SCAM message that is not held out and not a fragment, `NEW` is
`OLD` minus what `redundant_ids()` withholds. Curated chunks are identical in both.

```python
"""Before/after retrieval measurement for the near-duplicate dedup."""
import csv, re, sqlite3, sys
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer

REPO = "/path/to/Elderly-Scam-Shield"
sys.path.insert(0, f"{REPO}/knowledge-base")
from kb.dedupe import redundant_ids, similarity

MODEL = SentenceTransformer("intfloat/multilingual-e5-small")
enc_q = lambda ts: MODEL.encode([f"query: {t}" for t in ts], normalize_embeddings=True)
enc_p = lambda ts: MODEL.encode([f"passage: {t}" for t in ts], normalize_embeddings=True)

con = sqlite3.connect(f"{REPO}/knowledge-base/out/kb.sqlite")
curated = con.execute("""
    SELECT c.chunk_id, c.text, c.parent_type, l.scam_type
    FROM kb_chunks c
    LEFT JOIN lure_patterns l ON c.parent_type='lure_pattern' AND l.pattern_id=c.parent_id
    WHERE c.parent_type != 'message_example'
""").fetchall()
candidates = con.execute("""
    SELECT message_id, text, scam_type FROM message_examples
    WHERE label='SCAM' AND eval_holdout=0 AND LENGTH(TRIM(text)) >= 20
""").fetchall()
old_msgs = [(m, t, "message_example", st) for m, t, st in candidates]
withheld = redundant_ids([(m, t) for m, t, _ in candidates])
new_msgs = [c for c in old_msgs if c[0] not in withheld]
POOLS = {"OLD": curated + old_msgs, "NEW": curated + new_msgs}

rows = list(csv.DictReader(open(f"{REPO}/eval-set.csv")))
qvecs = enc_q([r["text"] for r in rows])
gold = [r["gold_label"].strip() for r in rows]

_NONID = re.compile(r"[^0-9a-zЀ-ӿ]+")
ik = lambda t: _NONID.sub("", str(t or "").lower())
by_key = {ik(t): (st, lb) for t, st, lb in
          con.execute("SELECT text, scam_type, label FROM message_examples")}
typed = [(i, by_key[ik(r["text"])][0]) for i, r in enumerate(rows)
         if ik(r["text"]) in by_key and by_key[ik(r["text"])][1] == "SCAM"
         and by_key[ik(r["text"])][0] not in (None, "unclassified")]

for name, pool in POOLS.items():
    scores = qvecs @ enc_p([c[1] for c in pool]).T   # same as store.py
    order = np.argsort(-scores, axis=1)
    topk = lambda qi, k: [pool[j] for j in order[qi, :k]]

    for k in (3, 6, 10):
        hits = sum(w in {c[3] for c in topk(qi, k)} for qi, w in typed)
        print(f"{name} recall@{k:<2} = {hits/len(typed):.3f}")

    distinct, ptypes = [], Counter()
    for qi in range(len(rows)):
        got = topk(qi, 6)
        ptypes.update({c[2] for c in got})
        reps = []
        for c in got:
            if not any(similarity(c[1], r) >= 0.8 for r in reps):
                reps.append(c[1])
        distinct.append(len(reps))
    print(f"{name} distinct in top-6: mean {np.mean(distinct):.3f} worst {min(distinct)}")
    print(f"{name} parent_types: {dict(ptypes)}")

    top6 = np.sort(scores, axis=1)[:, -6:].mean(axis=1)
    s = np.array([v for v, g in zip(top6, gold) if g == "SCAM"])
    l = np.array([v for v, g in zip(top6, gold) if g == "LEGIT"])
    thr = np.linspace(min(s.min(), l.min()), max(s.max(), l.max()), 400)
    acc = max((np.sum(s >= x) + np.sum(l < x)) / (len(s) + len(l)) for x in thr)
    print(f"{name} separation {s.mean()-l.mean():+.4f}  similarity-alone accuracy {acc:.3f}")
```

Expected: `OLD` reproduces the 2026-08-08 figures exactly — recall 0.800 / 0.800 / 0.829,
separation +0.0336, accuracy 0.835, parent types `{message_example: 85, advisory: 11,
lure_pattern: 1, brand_rebuttal: 1}`. If it does not, the harness is wrong, not the KB.
