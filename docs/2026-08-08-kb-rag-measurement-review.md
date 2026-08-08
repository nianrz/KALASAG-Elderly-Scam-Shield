---
title: "KB / RAG measurement review — kb-changes branch"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
owner: Aki (QA)
updated: 2026-08-08
tags: [capstone, kalasag, eval, rag, retrieval, measurement, handoff]
---

# KB / RAG measurement review — `kb-changes`

**From:** Aki (QA) · **For:** whoever picks up the eval work next
**Branch reviewed:** `kb-changes` at `db1adc1`, 11 commits ahead of `main`, 0 behind, fast-forwardable.

This is a review of whether the eval-set rebalance on `kb-changes` actually improves anything, plus the retrieval-level measurement framework that did not previously exist in the repo. Every number below is from a run on this branch on 2026-08-08. Nothing is estimated.

---

## Do this first

**Rebuild the KB before you run anything or trust any test result.**

```bash
cd /path/to/Elderly-Scam-Shield
knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
```

Expect `kb_chunks: 715`. If you skip this step, two tests fail and pipeline invariant 5 is live-violated. See [The blocker](#the-blocker-the-kb-was-never-rebuilt).

---

## The blocker: the KB was never rebuilt

`kb-changes` shipped the new holdout code and the new `build_report.json`, but not the database either one describes.

| | claimed in `build_report.json` | actual in `kb.sqlite` |
|---|---|---|
| `kb_chunks` | 715 | **732** |
| retrievable messages | 675 | **692** |
| `eval_holdout` rows | 88 | **53** |

`knowledge-base/out/kb.sqlite` is gitignored (`.gitignore:31`), so the branch could be committed, reviewed, and merged with the artifact silently a build behind. The file on disk was dated 2026-08-06 — pre-rebalance.

Two consequences:

1. **`backend/tests/test_holdout.py` failed 2/2** — `test_no_retrievable_message_matches_eval_text` and `test_fragments_are_not_retrievable`. The tests are correct; the artifact was stale. Suite was `2 failed, 88 passed`.
2. **Pipeline invariant 5 was violated 13 times.** Thirteen of the 85 eval messages were sitting in the retrievable pool, so the Detector could retrieve answers to its own test.

After `build_kb.py`: 715 chunks, 675 retrievable, 88 held out, **0 leaks**, backend **90 passed**, knowledge-base **55 passed**.

> **This is a process gap, not a one-off.** Anyone who checks out this branch fresh gets a red suite until they rebuild, and the rebuild step is documented nowhere. `docs/DEPLOYMENT.md` checks `chunk_count` post-deploy, which catches it late; `docs/TASKS.md` and `qa/TEST-PLAN.md` do not mention it at all. Recommended: add the rebuild to the deploy preflight in `CLAUDE.md` and to `qa/TEST-PLAN.md` as a precondition for the backend suite.

---

## Is the branch better?

It changes the *test* and the *system*. These need separate answers — comparing F1-on-85 against F1-on-55 is a moved goalpost, not a measurement.

### As a fix to the system: yes, but smaller than the diff suggests

The 13 leaks decompose as:

| cause | count | fixed by |
|---|---|---|
| stale build — the 30 newly-added eval messages were never held out | 12 | `build_kb.py` |
| whitespace-twin bug the `identity_key` rewrite targets | 1 | `normalise.py` change |

The one message is `msg01484`, the W19 Games twin of `msg01483` differing by a single space before the URL — exactly the case the new docstring describes. Under the old whitespace-preserving key neither string is a prefix of the other, so `msg01484` stayed retrievable while its twin was eval row M010.

So the `normalise.py` rewrite (`normalise_text` → `identity_key`, `MIN_PREFIX_LEN 24` → `MIN_KEY_LEN 20`) is a real correctness fix worth **one message**. The other twelve needed a rebuild, not a code change. Both were necessary; the code change is the smaller half.

### As a better test: yes, and this is the stronger result

Every arithmetic claim in `docs/superpowers/specs/2026-08-07-eval-set-rebalance-design.md` verifies independently:

| claim | verified |
|---|---|
| 55 rows contain 51 unique messages | yes — dropping M020/M015/M054/M053 gives 51 |
| post-dedup split is 33 SCAM / 18 LEGIT | yes |
| 5 rows truncated at 400 chars | yes — exactly M039, M041, M045, M049, M054 |
| new set is 85 rows, all unique | yes — 45 SCAM / 40 LEGIT, 38 easy / 47 hard |
| 47 old texts carry over verbatim | yes (51 kept − 4 remaining truncated; M054 was also a dupe) |

**`has_link → SCAM` baseline falls F1 0.985 → 0.660** (accuracy 0.612, precision 0.615, recall 0.711; tp 32 / fp 20 / tn 20 / fn 13). Class balance improves 33/18 → 45/40. The confound the rebalance was written to break is broken.

One incidental confirmation: a naive link-detection regex scores F1 0.321 on the new set and disagrees with the hand-assigned `has_link` column on **22 of 85 rows**. The spec's insistence on hand-assignment over automated detection is justified — do not "simplify" `baseline_confusion` to detect links.

---

## How to measure the KB and RAG system

**There were no retrieval-level metrics anywhere in the repo.** The only eval is end-to-end verdict F1, which structurally cannot see whether retrieval contributes anything: if the KB returned pure noise and the Detector still classified correctly from the message text alone, F1 would not move.

Four metrics, all zero LLM calls, all runnable in under a minute. Results from this branch post-rebuild:

### 1. Holdout enforcement at the retrieval surface

Binary pass/fail on invariant 5. Not "does the DB have the flag set" but "can `ChunkStore.search` reach an eval message". **Result: 0 reachable.**

This is the one metric that must be gated in CI. It is already partly covered by `test_holdout.py`, but that tests the database; this tests the search surface.

### 2. `scam_type` recall@k

For each held-out SCAM with a known `scam_type`, does top-k retrieval surface at least one chunk of the matching type? (n = 35)

| k | recall |
|---|---|
| 3 | 0.800 |
| 6 | 0.800 |
| 10 | 0.829 |

**`recall@3 == recall@6`.** Chunks 4–6 contribute zero additional same-type evidence. `TOP_K = 6` in `backend/app/graph/nodes/retrieve.py` is buying Detector context tokens for nothing. Worth testing 3 — but check the advisory / `brand_rebuttal` path first, since those chunks are rarer and may rely on the wider window (see metric 3).

Caveat on this number: the retrievable pool is heavily skewed — 406 of 715 chunks are `casino` and 207 have no `scam_type` at all. 0.800 is measured against that distribution, not a balanced one.

### 3. Coverage and evidence density

Over all 85 eval messages at `top_k=6`: **0 queries returned nothing**, **0 queries returned no `message_example`**. Parent-type appearances across the 85 queries: `message_example` 85, `advisory` 11, `lure_pattern` 1, `brand_rebuttal` 1.

The `lure_pattern` and `brand_rebuttal` chunks almost never surface. That is not necessarily wrong — hotlines and rebuttals are read by key, per invariant 2 — but it means the 10 lure patterns are doing very little retrieval work and the deck should not claim otherwise.

### 4. Similarity separation — and a confound the branch does not close

Mean cosine similarity of the top-6 chunks, by gold label:

| | mean | sd |
|---|---|---|
| gold SCAM (n=45) | 0.8870 | 0.0272 |
| gold LEGIT (n=40) | 0.8534 | 0.0127 |
| separation | **+0.0336** | |

**Thresholding on that similarity alone reaches 0.835 accuracy** (at 0.8610), with zero LLM calls.

This matters more than anything else in this document. The branch added a `has_link` control at F1 0.660 — but raw nearest-neighbour similarity to the KB is a *stronger* trivial baseline than the one being reported, and no report shows it. **If the pipeline scores below ~0.835 accuracy, it loses to a dot product.** The confound the rebalance set out to kill is still present in a different form, and it is the same question a panelist will ask.

Recommended: report the similarity baseline alongside `has_link` in every eval report. Same zero-cost control, closer to the real ceiling.

---

## What has not been measured

**The end-to-end pipeline number.** `backend/eval/results/` is empty on both branches — there is no stored prior run to compare against. The 0.985 and 0.660 figures are hand-computed baselines, not pipeline results. A full run is 85 messages × ~4 calls ≈ 340 calls at ~20s, roughly two hours of sandbox quota.

**Agreed plan for the next person, in priority order:**

1. **Retrieval ablation (~680 calls).** Run the 85-message eval twice — retrieval enabled, then retrieval disabled (empty context) — and compare F1. This is the only test that shows whether the RAG system contributes anything at all, and there is no cheaper substitute. It needs a `--no-retrieval` flag in `run_eval.py` that makes the retrieve node return `{"concepts_en": [], "retrieved": []}` without the LLM hop.
2. **Add the similarity baseline to `run_eval.py`.** Alongside `baseline_confusion`. Zero marginal cost per run. Pin it in `backend/tests/test_eval.py` the way 0.660 is pinned.
3. **Document the KB rebuild step.** `qa/TEST-PLAN.md` as a suite precondition, and the deploy preflight in `CLAUDE.md`.
4. **Investigate `TOP_K` 6 → 3.** Only after 1 and 2, and only with the `advisory` path checked.

Not started: none of the above. This branch is unchanged apart from this document.

---

## Reproducing the measurements

Both scripts are standalone and need no LLM credentials. `retrieval_quality.py` must run under the backend venv (`cd backend && uv run python …`) because it imports `app.retrieval`.

### Leak test

```python
"""Measure eval-set leakage into the retrievable pool. No LLM calls."""
import csv, re, sqlite3

REPO = "/path/to/Elderly-Scam-Shield"

# main's logic: normalise_text + prefix, MIN_PREFIX_LEN = 24
_WS = re.compile(r"\s+")
_EDGE = re.compile(r"^[\s.!?,;:\-–—'\"]+|[\s.!?,;:\-–—'\"]+$")
def normalise_text(t):
    if t is None: return ""
    return _EDGE.sub("", _WS.sub(" ", str(t)).strip().lower())
def holdout_old(texts):
    seen = {normalise_text(t) for t in texts}
    return sorted({t for t in seen if len(t) >= 24}, key=len, reverse=True)
def held_old(c, idx):
    n = normalise_text(c)
    return bool(n) and any(n == e or n.startswith(e) for e in idx)

# kb-changes' logic: identity_key, MIN_KEY_LEN = 20
_NONID = re.compile(r"[^0-9a-zЀ-ӿ]+")
def identity_key(t):
    if t is None: return ""
    return _NONID.sub("", str(t).lower())
def holdout_new(texts):
    keys = {identity_key(t) for t in texts}
    return sorted({k for k in keys if len(k) >= 20}, key=len, reverse=True)
def held_new(c, idx):
    k = identity_key(c)
    return bool(k) and any(k == e or k.startswith(e) for e in idx)

eval_rows = list(csv.DictReader(open(f"{REPO}/eval-set.csv")))
eval_texts = [r["text"] for r in eval_rows]
con = sqlite3.connect(f"{REPO}/knowledge-base/out/kb.sqlite")
msgs = con.execute(
    "SELECT message_id, text, retrievable, eval_holdout FROM message_examples"
).fetchall()

idx_old, idx_new = holdout_old(eval_texts), holdout_new(eval_texts)
retrievable = [m for m in msgs if m[2] == 1]
print(f"retrievable={len(retrievable)} eval_holdout={sum(1 for m in msgs if m[3] == 1)}")

leak_old = [m for m in retrievable if held_old(m[1], idx_old)]
leak_new = [m for m in retrievable if held_new(m[1], idx_new)]
print(f"leaks by main's rule      : {len(leak_old)}")
print(f"leaks by identity_key rule: {len(leak_new)}")
print(f"caught ONLY by identity_key: {len(set(leak_new) - set(leak_old))}")
for mid, text, _, _ in set(leak_new) - set(leak_old):
    print(f"  {mid}: {text[:90]!r}")
```

Expected on a correctly built KB: `retrievable=675 eval_holdout=88`, all three leak counts `0`.
Expected on the stale 2026-08-06 KB: `retrievable=692 eval_holdout=53`, leaks `12 / 13 / 1`.

### Retrieval quality

```python
"""Retrieval-level metrics. Zero LLM calls — embeddings only."""
import csv, re, sqlite3, sys
from collections import Counter
import numpy as np
sys.path.insert(0, "/path/to/Elderly-Scam-Shield/backend")
from app.retrieval.store import ChunkStore
from app.retrieval.embedder import embed_queries

REPO = "/path/to/Elderly-Scam-Shield"
_NONID = re.compile(r"[^0-9a-zЀ-ӿ]+")
ik = lambda t: _NONID.sub("", str(t or "").lower())

rows = list(csv.DictReader(open(f"{REPO}/eval-set.csv")))
con = sqlite3.connect(f"{REPO}/knowledge-base/out/kb.sqlite")
by_key = {ik(t): (st, lb) for t, st, lb in con.execute(
    "SELECT text, scam_type, label FROM message_examples")}

store = ChunkStore()
print(f"{len(store._chunks)} chunks, dim={store._vectors.shape}")
print(f"scam_type mix: {dict(Counter(c.scam_type for c in store._chunks))}")

# 1. holdout enforcement at the search surface
eval_keys = {ik(r["text"]) for r in rows}
served = [c for c in store._chunks if ik(c.text) in eval_keys
          or any(ik(c.text).startswith(k) for k in eval_keys if len(k) >= 20)]
print(f"[1] eval chunks reachable by search: {len(served)}  (must be 0)")

# 2. scam_type recall@k
typed = [(r, by_key[ik(r["text"])][0]) for r in rows
         if ik(r["text"]) in by_key and by_key[ik(r["text"])][1] == "SCAM"
         and by_key[ik(r["text"])][0] not in (None, "unclassified")]
print(f"[2] scam_type recall@k (n={len(typed)})")
for k in (3, 6, 10):
    hits = sum(want in {c.scam_type for c in store.search([r["text"]], top_k=k)}
               for r, want in typed)
    print(f"    recall@{k:<2} = {hits}/{len(typed)} = {hits/len(typed):.3f}")

# 3. coverage
pt = Counter()
empties = 0
for r in rows:
    got = store.search([r["text"]], top_k=6)
    empties += not got
    pt.update({c.parent_type for c in got})
print(f"[3] empty queries={empties}  parent_type appearances={dict(pt)}")

# 4. similarity separation
def topsim(texts):
    return np.sort(embed_queries(texts) @ store._vectors.T, axis=1)[:, -6:].mean(axis=1)
s = topsim([r["text"] for r in rows if r["gold_label"].strip() == "SCAM"])
l = topsim([r["text"] for r in rows if r["gold_label"].strip() == "LEGIT"])
print(f"[4] SCAM {s.mean():.4f} (sd {s.std():.4f}) / "
      f"LEGIT {l.mean():.4f} (sd {l.std():.4f}) / sep {s.mean()-l.mean():+.4f}")
thr = np.linspace(min(s.min(), l.min()), max(s.max(), l.max()), 400)
acc, t = max(((np.sum(s >= x) + np.sum(l < x)) / (len(s)+len(l)), x) for x in thr)
print(f"    accuracy from similarity ALONE: {acc:.3f} at {t:.4f}")
```

---

## Merge assessment

`kb-changes` is sound and fast-forwardable, with two conditions:

1. **The KB must be rebuilt** by whoever merges, and `chunk_count` confirmed as 715 before the next deploy. `docs/DEPLOYMENT.md` and `CLAUDE.md` already expect 715, so a deploy from a stale tree will fail its own preflight check.
2. **`knowledge-base/` is Nian's directory** and this branch edits `kb/normalise.py`, `scripts/build_kb.py`, `scripts/verify_kb.py`, `content/lure_patterns.yaml`, and `tests/test_normalise.py`. That crosses the ownership boundary in `CLAUDE.md`. The changes are correct and test-covered, but Nian should see them before merge.
