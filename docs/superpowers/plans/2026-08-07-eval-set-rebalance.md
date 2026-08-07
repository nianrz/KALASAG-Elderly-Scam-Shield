# Eval Set Rebalance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance the eval set from 55 to 85 messages so it measures the pipeline rather than link presence, and repair the integrity defects that make today's numbers wrong.

**Architecture:** The eval CSV is the source of truth for holdout. `build_kb.py` reads it, normalises every corpus message, and marks any match `eval_holdout=1, retrievable=0`. So adding rows to the CSV and rebuilding is the whole holdout mechanism — no manual flag flipping. Work proceeds: harden the matcher, rename the file, fix the existing rows, add the new rows, rebuild, then teach the harness to report its own control.

**Tech Stack:** Python 3.14, `uv`, pytest, SQLite. KB build scripts run under `knowledge-base/.venv` (separate from the backend venv).

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-08-07-eval-set-rebalance-design.md`. Read it before Task 1.
- **Final size:** n = 85 — 51 kept + 12 link-free SCAM + 22 link-bearing LEGIT.
- **Final composition:** SCAM 45 (15 link-free / 30 link-bearing), LEGIT 40 (18 link-free / 22 link-bearing).
- **Expected regex baseline after rebalance:** F1 0.618, accuracy 0.565, precision 0.577, recall 0.667. Tolerance ±0.05 on F1.
- **Expected `chunk_count` after rebuild: 719** (732 − 12 newly held-out SCAM chunks − 1 for `msg01484`).
- **`has_link` is assigned by hand, never computed.** Three successive detectors disagreed with the truth; the KB's own `has_url` is wrong on 199/1571 rows.
- **Never edit `knowledge-base/out/kb.sqlite` directly.** It is a build artifact. Change `content/` or the scripts, then rebuild.
- Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `chore:`. No `Co-Authored-By` trailers.
- Do not push. Local commits only.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `knowledge-base/kb/normalise.py` | Holdout identity key | Modify — whitespace/punctuation-insensitive key |
| `knowledge-base/tests/test_normalise.py` | Matcher tests | Modify — add the M010 regression case |
| `eval-set.csv` | The gold set | Rename from `eval-set-candidate-55.csv`, then rewrite |
| `backend/eval/run_eval.py` | Eval harness | Modify — path, regex baseline, `--language` |
| `backend/tests/test_eval.py` | Harness tests | Modify — baseline metric tests |
| `backend/tests/test_holdout.py` | Invariant 5 in CI | **Create** — asserts no eval text is retrievable |
| `knowledge-base/scripts/build_kb.py` | KB build | Modify — path only |
| `knowledge-base/scripts/verify_kb.py` | KB checks | Modify — path, fragment check |
| `knowledge-base/content/lure_patterns.yaml` | Lure copy | Modify — prevalence claim |
| `scripts/` (repo root, transient) | Row extraction | Create then delete — not committed |

---

### Task 1: Harden the holdout identity key

The M010 leak is one space. `msg01483` ends `na!w1903b.xyz`; `msg01484` ends `na! w1903b.xyz`. `normalise_text` collapses runs of whitespace but does not remove it, so neither string is a prefix of the other and `msg01484` stayed `retrievable=1` — a message identical to eval row M010 sitting in the pool the Detector retrieves from.

**Files:**
- Modify: `knowledge-base/kb/normalise.py`
- Test: `knowledge-base/tests/test_normalise.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `identity_key(text: str) -> str`, `holdout_index(eval_texts: Iterable[str]) -> list[str]`, `is_held_out(candidate: str, eval_norms: list[str]) -> bool`. `normalise_text` keeps its current signature and behaviour — other callers use it for display.

- [ ] **Step 1: Write the failing tests**

Append to `knowledge-base/tests/test_normalise.py`:

```python
from kb.normalise import holdout_index, identity_key, is_held_out


def test_identity_key_ignores_whitespace_and_punctuation():
    """The M010 leak: msg01483 and msg01484 differ by one space."""
    a = "W19 Games, sumali ka na!w1903b.xyz"
    b = "W19 Games, sumali ka na! w1903b.xyz"
    assert identity_key(a) == identity_key(b)


def test_is_held_out_catches_whitespace_variant():
    held = "W19 Games, ang tanging platform sa Pilipinas na tumatanggap ng GCash para sa mga deposito at withdrawal. Sumali ka na!w1903b.xyz"
    variant = held.replace("na!w1903b", "na! w1903b")
    assert is_held_out(variant, holdout_index([held]))


def test_is_held_out_still_matches_truncated_prefix():
    """The 400-char truncation rule must survive the change."""
    full = "Get up to P2K Cashback with min. required spend at SM Appliance Center with your BDO Credit Card, terms apply"
    assert is_held_out(full, holdout_index([full[:60]]))


def test_is_held_out_rejects_unrelated_message():
    assert not is_held_out(
        "Your Pag-IBIG Multi-Purpose Loan has been approved, claim it at any branch",
        holdout_index(["W19 Games, sumali ka na!w1903b.xyz"]),
    )


def test_short_texts_are_not_holdout_evidence():
    """A 'Hello' in the eval set must not hold out every message starting with it."""
    assert holdout_index(["Hello", "Hi po"]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd knowledge-base && .venv/bin/pytest tests/test_normalise.py -v
```

Expected: FAIL — `ImportError: cannot import name 'identity_key'`.

- [ ] **Step 3: Implement**

In `knowledge-base/kb/normalise.py`, add `identity_key` and rewrite the two holdout functions to use it. Leave `normalise_text` untouched.

```python
# Characters that carry identity. Latin and Cyrillic both appear in the corpus —
# scammers use Cyrillic homoglyph domains (9910.омск.рус).
_NON_IDENTITY = re.compile(r"[^0-9a-zЀ-ӿ]+")

# Below this length a prefix match is too weak to be evidence of identity.
# Lower than MIN_PREFIX_LEN because identity_key strips characters.
MIN_KEY_LEN = 20


def identity_key(text: str) -> str:
    """Aggressive key for 'is this the same message?'.

    Lowercases and drops everything that is not alphanumeric, so the same
    message survives whitespace jitter, punctuation drift, and re-wrapping.
    Used only for holdout matching; never for display or storage.
    """
    if text is None:
        return ""
    return _NON_IDENTITY.sub("", str(text).lower())
```

Then replace the bodies of `holdout_index` and `is_held_out`:

```python
def holdout_index(eval_texts: Iterable[str]) -> list[str]:
    """Identity keys of the eval set, de-duplicated, non-trivial, longest first."""
    keys = {identity_key(t) for t in eval_texts}
    usable = {k for k in keys if len(k) >= MIN_KEY_LEN}
    return sorted(usable, key=len, reverse=True)


def is_held_out(candidate: str, eval_norms: list[str]) -> bool:
    """True if candidate equals, or begins with, any eval-set message."""
    key = identity_key(candidate)
    if not key:
        return False
    return any(key == e or key.startswith(e) for e in eval_norms)
```

Update the module docstring — the prefix rule's justification is unchanged, but the whitespace reason is new:

```python
"""Text normalisation and eval-set holdout matching.

The holdout rule is exact-or-prefix over an aggressive identity key, not
over display text. Two reasons, both measured against the corpus:

  * The eval CSV truncated message text at 400 characters; five rows hit
    that cap and are strict prefixes of longer corpus messages. Exact
    matching alone let all five leak.
  * Corpus messages drift by whitespace and punctuation around an
    identical template. msg01483 and msg01484 differ by a single space
    before the URL; under a whitespace-preserving key neither is a prefix
    of the other, and msg01484 stayed retrievable while its twin was the
    eval set's M010.

Letting either through lets the Detector retrieve the answers to its own
evaluation. See pipeline invariant 5 in CLAUDE.md.
"""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd knowledge-base && .venv/bin/pytest tests/ -v
```

Expected: PASS, including the pre-existing `test_normalise.py` cases.

- [ ] **Step 5: Confirm the fix catches exactly the two known rows and nothing else**

```bash
cd knowledge-base && .venv/bin/python -c "
import csv, sqlite3, sys; sys.path.insert(0,'.')
from kb.normalise import holdout_index, is_held_out
texts=[r['text'] for r in csv.DictReader(open('../eval-set-candidate-55.csv'))]
idx=holdout_index(texts)
con=sqlite3.connect('out/kb.sqlite')
rows=list(con.execute('select message_id,text,eval_holdout from message_examples'))
now={r[0] for r in rows if is_held_out(r[1], idx)}
was={r[0] for r in rows if r[2]==1}
print('newly held out:', sorted(now-was))
print('regressions   :', sorted(was-now))
"
```

Expected exactly:
```
newly held out: ['msg00780', 'msg01484']
regressions   : []
```

`msg01484` is the M010 leak. `msg00780` is M044's twin — LEGIT, so it was never retrievable, but it was mis-flagged. Any other id, or any regression, means the key is too aggressive: stop and re-check `MIN_KEY_LEN`.

- [ ] **Step 6: Commit**

```bash
git add knowledge-base/kb/normalise.py knowledge-base/tests/test_normalise.py
git commit -m "fix: match eval holdout on an identity key, not display text

msg01484 differs from eval row M010 by a single space before the URL.
normalise_text collapses whitespace but does not remove it, so neither
string was a prefix of the other and msg01484 stayed retrievable — a
message identical to M010 in the pool the Detector retrieves from.

Matching now runs over an alphanumeric-only key. Catches msg01484 and
msg00780 with no regressions across the 1571-message corpus."
```

---

### Task 2: Rename the eval set to `eval-set.csv`

`eval-set-candidate-55.csv` encodes a size that is wrong at n=85 and would be wrong again at the next revision. Eleven files reference it; two of them (`build_kb.py`, `verify_kb.py`) read it to decide what to hold out, so a missed reference silently breaks the holdout rather than raising.

**Files:**
- Rename: `eval-set-candidate-55.csv` → `eval-set.csv`
- Modify: `backend/eval/run_eval.py:29`, `knowledge-base/scripts/build_kb.py:41`, `knowledge-base/scripts/verify_kb.py:119`, `backend/tests/fixtures/make_fixture.py` (comments only, lines 28 and 131)
- Modify: `CLAUDE.md:137`, `docs/ARCHITECTURE.md:98`, `docs/GUIDE.md:148`, `qa/TEST-PLAN.md:76`

**Interfaces:**
- Consumes: nothing.
- Produces: the path `<repo>/eval-set.csv`, referenced as `BACKEND_ROOT.parent / "eval-set.csv"` in `run_eval.py` and `REPO / "eval-set.csv"` in the KB scripts.

- [ ] **Step 1: Rename with history preserved**

```bash
git mv eval-set-candidate-55.csv eval-set.csv
```

- [ ] **Step 2: Update the four code references**

```bash
sed -i '' 's/eval-set-candidate-55\.csv/eval-set.csv/g' \
  backend/eval/run_eval.py \
  knowledge-base/scripts/build_kb.py \
  knowledge-base/scripts/verify_kb.py \
  backend/tests/fixtures/make_fixture.py
```

- [ ] **Step 3: Update the four live docs**

```bash
sed -i '' 's/eval-set-candidate-55\.csv/eval-set.csv/g' \
  CLAUDE.md docs/ARCHITECTURE.md docs/GUIDE.md qa/TEST-PLAN.md
```

**Do not touch** `docs/superpowers/specs/2026-08-05-scam-shield-knowledge-base-design.md` or `docs/superpowers/plans/2026-08-06-scam-shield-knowledge-base.md`. Those record what the file was called when they were written — the same reasoning `CLAUDE.md` applies to pre-rename "Elderly Scam Shield" references.

- [ ] **Step 4: Verify no live reference survives**

```bash
grep -rn "eval-set-candidate-55" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules .
```

Expected: only the two historical files above, plus the new spec and this plan (which quote the old name deliberately).

- [ ] **Step 5: Run both suites**

```bash
cd backend && uv run pytest -q && cd ../knowledge-base && .venv/bin/pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: rename eval-set-candidate-55.csv to eval-set.csv

The old name encoded a size that is wrong at n=85 and would be wrong
again at the next revision. Historical specs keep the old name."
```

---

### Task 3: Repair the existing 51 rows

Four defects, all of which change the metrics on their own: 4 duplicate rows (two pairs resolve to the *same* corpus row and were double-weighted in every run to date), 5 rows truncated at exactly 400 characters, an empty `notes_for_lui` column, and a `difficulty` column that is a second copy of `gold_label`.

**Files:**
- Modify: `eval-set.csv`
- Create (transient, do not commit): `scripts/rebuild_eval_set.py`

**Interfaces:**
- Consumes: `identity_key` from Task 1.
- Produces: `eval-set.csv` with header `id,source_category,gold_label,has_link,hardness,text,notes_for_lui` and 51 data rows.

- [ ] **Step 1: Write the rebuild script**

Create `scripts/rebuild_eval_set.py`:

```python
"""Rebuild eval-set.csv: drop duplicates, restore truncated text.

Transient. Run once, verify, delete. Not committed — the CSV is the artifact.
"""
import csv, sqlite3, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "knowledge-base"))
from kb.normalise import identity_key  # noqa: E402

# Second of each pair; both members are identical messages.
# M049/M054 and M051/M053 resolve to the same corpus row, msg00246.
DUPES = {"M020", "M015", "M054", "M053"}

con = sqlite3.connect(REPO / "knowledge-base/out/kb.sqlite")
corpus = list(con.execute("select text from message_examples"))
by_key = {}
for (text,) in corpus:
    by_key.setdefault(identity_key(text), text)

rows = list(csv.DictReader(open(REPO / "eval-set.csv", encoding="utf-8")))
out = []
restored = []
for r in rows:
    if r["id"] in DUPES:
        continue
    text = r["text"]
    if len(text) == 400:
        # Truncated at the cap. Find the corpus message it is a prefix of.
        key = identity_key(text)
        full = next((v for k, v in by_key.items() if k.startswith(key)), None)
        if full is None:
            raise SystemExit(f"{r['id']}: no corpus message extends this text")
        restored.append((r["id"], len(text), len(full)))
        text = full
    out.append({
        "id": r["id"],
        "source_category": r["source_category"],
        "gold_label": r["gold_label"],
        "has_link": "",      # assigned by hand in Step 3
        "hardness": "",      # assigned by hand in Step 3
        "text": text,
        "notes_for_lui": "",
    })

with open(REPO / "eval-set.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=[
        "id", "source_category", "gold_label", "has_link", "hardness",
        "text", "notes_for_lui"])
    w.writeheader()
    w.writerows(out)

print(f"kept {len(out)} rows (dropped {len(DUPES)})")
for mid, was, now in restored:
    print(f"  restored {mid}: {was} -> {now} chars")
```

- [ ] **Step 2: Run it**

```bash
cd /Users/nathanaelian/Documents/Uni/Term9/KALASAG-Elderly-Scam-Shield
knowledge-base/.venv/bin/python scripts/rebuild_eval_set.py
```

Expected:
```
kept 51 rows (dropped 4)
  restored M039: 400 -> 459 chars
  restored M041: 400 -> 467 chars
  restored M045: 400 -> 459 chars
  restored M049: 400 -> 660 chars
```

M054 is a dropped duplicate, so only four rows restore.

- [ ] **Step 3: Fill `has_link`, `hardness`, and `notes_for_lui` by hand**

Open `eval-set.csv` and complete the three empty columns for all 51 rows. **Read each message.** `has_link` is not computable — the corpus contains digit-only domains (`6384.de/yvJl`), bare IPs (`38.11.89.109`), Cyrillic IDNs (`9910.омск.рус`), brace-wrapped links (`{ kklfph.fyi }`), and spaced dots (`gmail. com`).

- `has_link` — `yes` / `no`. Expected totals for the kept 51: 30 SCAM yes, 3 SCAM no, 0 LEGIT yes, 18 LEGIT no.
- `hardness` — `easy` / `hard`. A row is `hard` when the obvious surface cue points the wrong way or is absent. Most of the kept 51 are `easy`; that is the finding, not a problem to hide.
- `notes_for_lui` — one line on what makes the row what it is. This is the column Lui writes the paper from.

- [ ] **Step 4: Verify structure**

```bash
python3 -c "
import csv, collections
rows=list(csv.DictReader(open('eval-set.csv')))
assert len(rows)==51, len(rows)
assert not [r for r in rows if len(r['text'])==400], 'truncation fingerprint remains'
assert all(r['has_link'] in ('yes','no') for r in rows), 'has_link incomplete'
assert all(r['hardness'] in ('easy','hard') for r in rows), 'hardness incomplete'
assert all(r['notes_for_lui'].strip() for r in rows), 'notes incomplete'
print(collections.Counter((r['gold_label'],r['has_link']) for r in rows))
"
```

Expected: `Counter({('SCAM','yes'): 30, ('LEGIT','no'): 18, ('SCAM','no'): 3})`

- [ ] **Step 5: Commit**

```bash
git add eval-set.csv
git commit -m "fix: repair the eval set's 51 unique rows

Drops 4 duplicates — M049/M054 and M051/M053 resolve to the same corpus
row (msg00246) and were double-weighted in every eval run to date.

Restores 4 rows truncated at exactly 400 characters; the harness was
scoring the model on messages that end mid-sentence.

Replaces the difficulty column, which was a second copy of gold_label,
with hand-assigned has_link and hardness. Fills notes_for_lui."
```

---

### Task 4: Add the 34 rebalancing rows

**Files:**
- Modify: `eval-set.csv`
- Create (transient, do not commit): `scripts/add_eval_rows.py`

**Interfaces:**
- Consumes: the 51-row `eval-set.csv` from Task 3.
- Produces: the 85-row `eval-set.csv`. New ids `M056`–`M067` (SCAM) and `M068`–`M089` (LEGIT), continuing the existing sequence. Ids are not reused from the dropped duplicates.

- [ ] **Step 1: Write the append script**

Create `scripts/add_eval_rows.py`:

```python
"""Append the 34 curated rebalancing rows, pulled verbatim from the KB.

Message ids come from the design spec's curation tables. Transient: run
once, verify, delete.
"""
import csv, sqlite3, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# 12 link-free SCAMs. Curated, not sampled: only 26 of 692 unheld SCAM
# messages are genuinely link-free and 13 of those are usable.
SCAMS = [
    "msg00408", "msg00174", "msg00282", "msg00407", "msg00696", "msg00546",
    "msg00595", "msg01003", "msg01100", "msg01162", "msg01379", "msg01401",
]
# 22 link-bearing LEGITs. Seed 20260807, capped at 4 per vendor.
LEGITS = [
    "msg00217", "msg00219", "msg00262", "msg00598", "msg00813", "msg00814",
    "msg00815", "msg00818", "msg00851", "msg00989", "msg01277", "msg01287",
    "msg01334", "msg01345", "msg01385", "msg01443", "msg01446", "msg01466",
    "msg01532", "msg01543", "msg01821", "msg01872",
]

con = sqlite3.connect(REPO / "knowledge-base/out/kb.sqlite")

def fetch(mid):
    row = list(con.execute(
        "select text, label, source_category from message_examples where message_id=?",
        (mid,)))
    if not row:
        raise SystemExit(f"{mid} not in corpus")
    return row[0]

rows = list(csv.DictReader(open(REPO / "eval-set.csv", encoding="utf-8")))
assert len(rows) == 51, f"expected 51 rows, found {len(rows)}"

new = []
for i, mid in enumerate(SCAMS, start=56):
    text, label, cat = fetch(mid)
    assert label == "SCAM", f"{mid} is {label}"
    new.append({"id": f"M{i:03d}", "source_category": cat, "gold_label": "SCAM",
                "has_link": "no", "hardness": "hard", "text": text,
                "notes_for_lui": f"[{mid}] "})
for i, mid in enumerate(LEGITS, start=68):
    text, label, cat = fetch(mid)
    assert label == "LEGIT", f"{mid} is {label}"
    new.append({"id": f"M{i:03d}", "source_category": cat, "gold_label": "LEGIT",
                "has_link": "yes", "hardness": "hard", "text": text,
                "notes_for_lui": f"[{mid}] "})

with open(REPO / "eval-set.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows + new)

print(f"appended {len(new)} rows, total {len(rows)+len(new)}")
```

- [ ] **Step 2: Run it**

```bash
knowledge-base/.venv/bin/python scripts/add_eval_rows.py
```

Expected: `appended 34 rows, total 85`

- [ ] **Step 3: Verify each added row's `has_link` by reading it**

The script assumes `no` for all 12 SCAMs and `yes` for all 22 LEGITs. That is the curation's claim, not a measurement — **read all 34 and correct any that are wrong.** Three messages that looked link-free to every automated detector do carry links (`msg00965`, `msg00710`, `msg00659`); they are excluded from the SCAM list for that reason, but the same failure mode can hide in the rows that were included.

```bash
python3 -c "
import csv
for r in csv.DictReader(open('eval-set.csv')):
    if r['id'] >= 'M056':
        print(f\"{r['id']} {r['gold_label']:5} link={r['has_link']:3} | {r['text'][:120]}\")
"
```

- [ ] **Step 4: Finish `notes_for_lui` for the 34 new rows**

The script seeds each with its corpus id in brackets. Add the reason. For the SCAM rows, the spec's curation table has a one-line justification for each — use it. The point of these rows is that they carry no link, no impersonated brand, and no urgency deadline, so the note should say which cue is absent.

- [ ] **Step 5: Verify the target composition**

```bash
python3 -c "
import csv, collections
rows=list(csv.DictReader(open('eval-set.csv')))
assert len(rows)==85, len(rows)
c=collections.Counter((r['gold_label'],r['has_link']) for r in rows)
print(c)
tp,fn=c[('SCAM','yes')],c[('SCAM','no')]
fp,tn=c[('LEGIT','yes')],c[('LEGIT','no')]
p=tp/(tp+fp); r_=tp/(tp+fn); f1=2*p*r_/(p+r_)
print(f'regex baseline: acc={(tp+tn)/85:.3f} prec={p:.3f} rec={r_:.3f} f1={f1:.3f}')
assert abs(f1-0.618)<0.05, f'composition drifted: F1 {f1:.3f}'
keys={r['text'].lower().strip() for r in rows}
assert len(keys)==85, 'duplicate text'
"
```

Expected: `Counter({('SCAM','yes'):30, ('LEGIT','yes'):22, ('LEGIT','no'):18, ('SCAM','no'):15})` and `f1=0.618`.

- [ ] **Step 6: Delete the transient scripts and commit**

```bash
rm -rf scripts/
git add eval-set.csv
git commit -m "feat: rebalance the eval set to 85 messages

Adds 12 link-free SCAMs and 22 link-bearing LEGITs, breaking the
correlation that let 'if has_link: SCAM' score F1 0.952 on the old set.
The regex baseline now scores 0.618.

The SCAM additions are chat-bait and Telegram/Messenger lures — the class
an elderly Filipino is most likely to receive, and the class the set had
zero of. The LEGIT additions include five UnionBank loan offers with
links and prize framing, set directly against four link-free loan scams."
```

---

### Task 5: Rebuild the KB and pin invariant 5 in CI

Adding 34 rows to the CSV changes nothing until the KB is rebuilt: 12 of the SCAM additions are currently `retrievable=1` and chunked, so the Detector can retrieve them. The leak that produced this plan went unnoticed because nothing asserted invariant 5 outside a script nobody runs.

**Files:**
- Regenerate: `knowledge-base/out/kb.sqlite`, `knowledge-base/out/build_report.json`
- Create: `backend/tests/test_holdout.py`
- Modify: `CLAUDE.md:219`, `docs/GUIDE.md` (lines 450, 452, 489, 720, 1003, 1134)

**Interfaces:**
- Consumes: `eval-set.csv` (85 rows), `identity_key` from Task 1.
- Produces: a KB with `chunk_count == 719` and no retrievable message matching any eval text.

- [ ] **Step 1: Rebuild**

```bash
cd knowledge-base && .venv/bin/python scripts/build_kb.py
```

- [ ] **Step 2: Verify holdout and read the new chunk count**

```bash
cd knowledge-base && .venv/bin/python scripts/verify_kb.py
sqlite3 out/kb.sqlite "select count(*) from kb_chunks"
sqlite3 out/kb.sqlite "select eval_holdout, retrievable, count(*) from message_examples group by 1,2"
```

Expected: `verify_kb.py` all-clean; `chunk_count` **719**; 87 rows at `eval_holdout=1` (85 eval texts plus `msg01484` and `msg00780`, which are whitespace variants of held-out rows).

If the count is not 719, do not adjust the constant to match — find out why. A count *above* 719 means additions were not held out; *below* means the identity key is matching more than it should.

- [ ] **Step 3: Write the failing CI test**

Create `backend/tests/test_holdout.py`:

```python
"""Pipeline invariant 5: eval-set messages are held out of retrieval.

This ran only inside knowledge-base/scripts/verify_kb.py, which nobody runs
on a backend change. msg01484 — identical to eval row M010 but for one
space — sat in the retrievable pool undetected as a result.

identity_key is duplicated from knowledge-base/kb/normalise.py rather than
imported. That is deliberate: knowledge-base is a separate package with its
own venv and is not a backend dependency. An independent implementation is
also the stronger test — importing the matcher the build used would only
prove the build agrees with itself. If the two ever diverge, this test
fails, which is the correct outcome.
"""
import csv
import re
import sqlite3

import pytest

from app.config import get_settings

_NON_IDENTITY = re.compile(r"[^0-9a-zЀ-ӿ]+")
MIN_KEY_LEN = 20


def identity_key(text: str) -> str:
    return _NON_IDENTITY.sub("", str(text or "").lower())


@pytest.fixture(scope="module")
def kb():
    path = get_settings().kb_path
    if not path.exists():
        pytest.skip(f"KB not present at {path}")
    con = sqlite3.connect(path)
    yield con
    con.close()


@pytest.fixture(scope="module")
def eval_keys():
    path = get_settings().kb_path.parents[2] / "eval-set.csv"
    if not path.exists():
        pytest.skip("eval-set.csv not present")
    with open(path, encoding="utf-8", newline="") as fh:
        keys = {identity_key(r["text"]) for r in csv.DictReader(fh)}
    return sorted((k for k in keys if len(k) >= MIN_KEY_LEN), key=len, reverse=True)


def test_no_retrievable_message_matches_eval_text(kb, eval_keys):
    leaked = [
        mid
        for mid, text in kb.execute(
            "SELECT message_id, text FROM message_examples WHERE retrievable = 1"
        )
        if any(identity_key(text).startswith(k) for k in eval_keys)
    ]
    assert leaked == [], f"eval messages retrievable: {leaked}"


def test_no_chunk_belongs_to_a_held_out_message(kb):
    (count,) = kb.execute(
        "SELECT COUNT(*) FROM kb_chunks c JOIN message_examples m "
        "ON c.parent_id = m.message_id WHERE m.eval_holdout = 1"
    ).fetchone()
    assert count == 0, f"{count} chunks belong to held-out messages"
```

- [ ] **Step 4: Run it**

```bash
cd backend && uv run pytest tests/test_holdout.py -v
```

Expected: PASS against the rebuilt KB. To confirm the test can actually fail, temporarily set one held-out row back to `retrievable=1` in a scratch copy of the DB and re-run — a test that cannot fail is not a test. Restore afterwards.

- [ ] **Step 5: Update the chunk-count expectation everywhere**

`CLAUDE.md:219` hard-codes 732 as the redeploy pass condition; `docs/GUIDE.md` repeats it at six places. Leaving them stale makes the next deploy verification report a false failure.

```bash
sed -i '' 's/\b732\b/719/g' CLAUDE.md docs/GUIDE.md
grep -n "719\|732" CLAUDE.md docs/GUIDE.md
```

Read every hit. `docs/GUIDE.md:489` ("`embedding` is NULL for all 732 rows when the KB arrives") is a historical statement about the KB as delivered — if it reads as history, leave it and revert that one line.

- [ ] **Step 6: Run everything**

```bash
cd backend && uv run pytest -q && cd ../knowledge-base && .venv/bin/pytest -q
```

- [ ] **Step 7: Commit**

```bash
git add knowledge-base/out/kb.sqlite knowledge-base/out/build_report.json \
        backend/tests/test_holdout.py CLAUDE.md docs/GUIDE.md
git commit -m "fix: rebuild the KB against the 85-message eval set

Holds out the 34 additions; 12 were retrievable and chunked. chunk_count
732 -> 719, updated in the redeploy runbook and the guide.

Adds backend/tests/test_holdout.py so invariant 5 runs on every backend
change. It previously lived only in verify_kb.py, which is why the
msg01484 leak survived."
```

---

### Task 6: Report the regex baseline in the eval

An accuracy figure with no control is not evidence. The baseline costs zero LLM calls and is the difference between "the pipeline scores 0.9" and "the pipeline scores 0.9 where the trivial rule scores 0.62".

**Files:**
- Modify: `backend/eval/run_eval.py`
- Test: `backend/tests/test_eval.py`

**Interfaces:**
- Consumes: `metrics(counts)` and `confusion(records, threshold)`, already in `run_eval.py`.
- Produces: `baseline_confusion(rows: list[dict]) -> dict[str, int]` taking raw CSV rows (not `Record`s — the baseline never calls the model) and returning the same `{"tp","fp","tn","fn"}` shape `metrics` consumes. `render_markdown`'s signature becomes `(records, rows, model_id, threshold)` — `rows` is inserted as the **second** parameter.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_eval.py`:

```python
from eval.run_eval import baseline_confusion, metrics


def test_baseline_uses_the_hand_assigned_has_link_column():
    rows = [
        {"gold_label": "SCAM", "has_link": "yes"},
        {"gold_label": "SCAM", "has_link": "no"},
        {"gold_label": "LEGIT", "has_link": "yes"},
        {"gold_label": "LEGIT", "has_link": "no"},
    ]
    assert baseline_confusion(rows) == {"tp": 1, "fn": 1, "fp": 1, "tn": 1}


def test_baseline_on_the_old_composition_is_near_perfect():
    """The defect this rebalance fixes: 30/0/3/18 was F1 0.952."""
    rows = (
        [{"gold_label": "SCAM", "has_link": "yes"}] * 30
        + [{"gold_label": "SCAM", "has_link": "no"}] * 3
        + [{"gold_label": "LEGIT", "has_link": "no"}] * 18
    )
    assert metrics(baseline_confusion(rows))["f1"] == pytest.approx(0.952, abs=0.01)


def test_baseline_on_the_rebalanced_composition_is_weak():
    rows = (
        [{"gold_label": "SCAM", "has_link": "yes"}] * 30
        + [{"gold_label": "SCAM", "has_link": "no"}] * 15
        + [{"gold_label": "LEGIT", "has_link": "yes"}] * 22
        + [{"gold_label": "LEGIT", "has_link": "no"}] * 18
    )
    assert metrics(baseline_confusion(rows))["f1"] == pytest.approx(0.618, abs=0.01)
```

Add `import pytest` at the top of the file if it is not already there.

- [ ] **Step 2: Run to verify they fail**

```bash
cd backend && uv run pytest tests/test_eval.py -v
```

Expected: FAIL — `ImportError: cannot import name 'baseline_confusion'`.

- [ ] **Step 3: Implement**

Add to `backend/eval/run_eval.py`, after `confusion`:

```python
def baseline_confusion(rows: list[dict]) -> dict[str, int]:
    """Confusion matrix for the trivial rule: a link means SCAM.

    Reads the hand-assigned has_link column rather than detecting links.
    Detection is not reliable enough to build a control on — the corpus
    carries digit-only domains, bare IPs, Cyrillic IDNs, and spaced dots,
    and the KB's own has_url column is wrong on 199 of 1571 rows.
    """
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for row in rows:
        predicted = row["has_link"].strip().lower() == "yes"
        actual = row["gold_label"] == "SCAM"
        key = ("tp" if predicted else "fn") if actual else ("fp" if predicted else "tn")
        counts[key] += 1
    return counts
```

In `render_markdown`, insert `rows: list[dict]` as the second parameter — `def render_markdown(records, rows, model_id, threshold)` — and add this block immediately before `## Metrics`:

```python
        "## Baseline — has_link → SCAM",
        "",
        "Zero LLM calls. The pipeline's result is only meaningful above this line.",
        "",
        "| accuracy | precision | recall | F1 |",
        "|---|---|---|---|",
        f"| {b['accuracy']:.3f} | {b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} |",
        "",
```

with `b = metrics(baseline_confusion(rows))` computed alongside the existing `m = metrics(counts)`.

Update the call site in `run` (currently `run_eval.py:174`):

```python
out_path.write_text(render_markdown(
    records, rows, model_id, get_settings().confidence_threshold))
```

and reorder `render_markdown`'s signature to `(records, rows, model_id, threshold)`.

- [ ] **Step 4: Run to verify they pass**

```bash
cd backend && uv run pytest tests/test_eval.py -v
```

Expected: PASS.

- [ ] **Step 5: Smoke-test the report end to end**

```bash
cd backend && uv run python eval/run_eval.py --limit 3 --out /tmp/evalcheck
```

Expected: a report in `/tmp/evalcheck/` whose baseline section reflects the first 3 rows. This makes 12 real LLM calls.

- [ ] **Step 6: Commit**

```bash
git add backend/eval/run_eval.py backend/tests/test_eval.py
git commit -m "feat: report the has_link baseline alongside the eval result

An accuracy figure with no control is not evidence. On the old set the
trivial rule scored F1 0.952, which no report ever showed. The baseline
reads the hand-assigned has_link column rather than detecting links --
detection is the thing that proved unreliable."
```

---

### Task 7: Evaluate the English path

`run_eval.py:155` hardcodes `"tl"`, so the `en` output path has never been evaluated — despite `3351e24` having fixed a language-directive bug in exactly that path. A full second pass doubles a ~340-call run for a check that one stratum answers.

**Files:**
- Modify: `backend/eval/run_eval.py`
- Test: `backend/tests/test_eval.py`

**Interfaces:**
- Consumes: `run(limit, out_dir)` as it exists.
- Produces: `run(limit: int | None, out_dir: Path, language: str = "tl", subset: int | None = None) -> Path`. Output filename gains a `-en` suffix when `language == "en"` so the two runs do not overwrite each other.

- [ ] **Step 1: Write the failing test**

```python
def test_output_filename_distinguishes_language(tmp_path):
    from eval.run_eval import result_filename
    tl = result_filename("bedrock_converse:global.anthropic.claude-sonnet-5", "tl")
    en = result_filename("bedrock_converse:global.anthropic.claude-sonnet-5", "en")
    assert tl != en
    assert en.endswith("-en.md")
    assert ":" not in tl and "/" not in tl
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd backend && uv run pytest tests/test_eval.py::test_output_filename_distinguishes_language -v
```

Expected: FAIL — `cannot import name 'result_filename'`.

- [ ] **Step 3: Implement**

Extract the filename logic from `run` into a function:

```python
def result_filename(model_id: str, language: str) -> str:
    slug = model_id.replace(":", "_").replace("/", "_")
    suffix = "" if language == "tl" else f"-{language}"
    return f"{datetime.now():%Y%m%d-%H%M}-{slug}{suffix}.md"
```

Thread `language` and `subset` through `run`, replacing the hardcoded `"tl"` at line 155 with the parameter, and slicing `rows = rows[:subset]` when `subset` is set. Add the flags:

```python
    parser.add_argument("--language", choices=["tl", "en"], default="tl")
    parser.add_argument("--subset", type=int, default=None,
                        help="First N rows only. Use --language en --subset 15 "
                             "for the English spot-check.")
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd backend && uv run pytest tests/test_eval.py -v
```

- [ ] **Step 5: Document the two runs**

Add to `run_eval.py`'s module docstring:

```
Run: uv run python eval/run_eval.py [--limit N] [--out eval/results]

Full Filipino/Taglish run (85 messages, ~340 calls):
    uv run python eval/run_eval.py

English spot-check (15 messages, ~60 calls) — catches language-directive
regressions in the en path without paying for a second full pass:
    uv run python eval/run_eval.py --language en --subset 15
```

- [ ] **Step 6: Commit**

```bash
git add backend/eval/run_eval.py backend/tests/test_eval.py
git commit -m "feat: evaluate the English output path on a 15-message subset

run_eval hardcoded tl, so the en path was never evaluated despite 3351e24
having fixed a language-directive bug in it. A subset rather than a second
full pass: ~60 calls instead of ~340."
```

---

### Task 8: Correct the two KB defects

Both were found while measuring for this rebalance and are independent of it.

**Files:**
- Modify: `knowledge-base/content/lure_patterns.yaml`
- Modify: `knowledge-base/scripts/verify_kb.py`
- Regenerate: `knowledge-base/out/kb.sqlite`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: a corrected `click-this-link` entry and a `fragments_not_retrievable` check in `verify_kb.py`.

- [ ] **Step 1: Fix the prevalence claim**

`lure_patterns.click-this-link` currently reads *"Two-thirds of scam messages carry no link at all, so a link is a strong signal but its absence proves nothing."*

Measured against the corpus in the same database: **26 of 692** unheld SCAM messages are link-free — 3.8%, not 67%. Replace the first clause and keep the second, which is correct either way:

```yaml
    advice: >-
      Shortened links hide where they go and do not appear on blocklists.
      A link is a strong signal, but its absence proves nothing — the
      link-free scams in this corpus are chat-bait that moves the victim
      to Messenger or Telegram, where the pressure happens off-SMS.
```

If the two-thirds figure came from a cited source, keep it *with* the attribution and note that this corpus disagrees. Do not leave it stated as fact about scam messages generally.

- [ ] **Step 2: Stop fragments being retrievable**

Messages like `"Hello"`, `"getcash!!"`, and `"001204649"` are retrieval noise whatever their label. Add to `verify_kb.py`, following the existing check style around line 77:

```python
    (fragments,) = con.execute(
        "SELECT COUNT(*) FROM message_examples "
        "WHERE retrievable = 1 AND LENGTH(TRIM(text)) < 20"
    ).fetchone()
    check("fragments_not_retrievable", fragments == 0,
          f"{fragments} retrievable messages under 20 characters")
```

Then add the same length floor to `build_kb.py:66` so the build satisfies it:

```python
            "retrievable": int(
                label == "SCAM" and not held and len(text.strip()) >= 20
            ),
```

- [ ] **Step 3: Rebuild and verify**

```bash
cd knowledge-base && .venv/bin/python scripts/build_kb.py && .venv/bin/python scripts/verify_kb.py
sqlite3 out/kb.sqlite "select count(*) from kb_chunks"
```

Record the new `chunk_count` — dropping fragments lowers it again. Propagate the new number to `CLAUDE.md` and `docs/GUIDE.md` exactly as in Task 5 Step 5.

- [ ] **Step 4: Run both suites**

```bash
cd backend && uv run pytest -q && cd ../knowledge-base && .venv/bin/pytest -q
```

`backend/tests/test_holdout.py` must still pass.

- [ ] **Step 5: Commit**

```bash
git add knowledge-base/content/lure_patterns.yaml knowledge-base/scripts/verify_kb.py \
        knowledge-base/scripts/build_kb.py knowledge-base/out/ CLAUDE.md docs/GUIDE.md
git commit -m "fix: correct the click-this-link prevalence claim and drop fragments

The KB claimed two-thirds of scam messages carry no link. Measured
against the corpus shipping in the same database it is 26 of 692 — 3.8%.
The Advisor reads this table, so the claim was refutable on stage.

Also stops messages under 20 characters being retrievable. 'Hello',
'getcash!!' and '001204649' are labelled SCAM upstream and were valid
retrieval targets."
```

---

### Task 9: Update the docs the map requires

`CLAUDE.md`'s doc map makes this mandatory, not optional: scope and limitations go to `docs/PRD.md`, test strategy and coverage to `qa/TEST-PLAN.md`.

**Files:**
- Modify: `qa/TEST-PLAN.md`, `docs/PRD.md`, `knowledge-base/README.md`, `docs/ARCHITECTURE.md`

- [ ] **Step 1: `qa/TEST-PLAN.md`**

Line 76 describes "the 55-message gold set". Update to 85 and add: the new composition table, the regex baseline as a required control, that `has_link` is hand-assigned and why, the English subset run, and `backend/tests/test_holdout.py` as the CI home of invariant 5.

- [ ] **Step 2: `docs/PRD.md`**

Add to limitations, in the doc's existing voice:

> **Email and bare-URL inputs are not evaluated.** The pipeline accepts all three input types, but the evaluation corpus is SMS-only. Covering the other two would mean authoring synthetic messages, which would measure the authors rather than the product. Real-world accuracy on pasted emails and URLs is unmeasured.

Restate any success criterion phrased against the 55-message set, and state that the reported F1 is a discrimination score on a deliberately stratified set, not a field-prevalence estimate.

- [ ] **Step 3: `knowledge-base/README.md`**

Record the new holdout count, the `click-this-link` correction, the fragment floor, and the label-noise caveat: gold labels are inherited from the upstream Kaggle set; the eval set is hand-reviewed, the retrieval corpus is not. In the 26-message slice that was checked, 10 were mislabelled or unlabelable.

- [ ] **Step 4: `docs/ARCHITECTURE.md`**

Line 98 lists the eval file in the repo layout — already renamed in Task 2. Update the eval report contract only if the doc describes `render_markdown`'s output as an interface.

- [ ] **Step 5: Verify the docs match reality**

```bash
grep -rn "55-message\|55 messages\|eval-set-candidate" docs/ qa/ knowledge-base/README.md CLAUDE.md \
  | grep -v superpowers/
```

Expected: no hits outside `docs/superpowers/`.

- [ ] **Step 6: Commit**

```bash
git add qa/TEST-PLAN.md docs/PRD.md knowledge-base/README.md docs/ARCHITECTURE.md
git commit -m "docs: record the 85-message eval set and its limits

Composition and the regex-baseline control in the test plan. Email and
bare-URL inputs recorded in the PRD as unevaluated rather than quietly
uncovered. Label-noise caveat in the KB README: the eval set is
hand-reviewed, the retrieval corpus is inherited unreviewed."
```

---

### Task 10: Run the eval and record the result

The point of all of it. Roughly 340 calls at ~20s; expect 30–60 minutes.

- [ ] **Step 1: Confirm the KB is the real one, not the fixture**

```bash
cd backend && uv run python -c "
from app.config import get_settings
from app.retrieval.store import ChunkStore
print(get_settings().kb_path, ChunkStore().chunk_count)
"
```

`chunk_count` is a property, not a method — no parentheses.

Expected: the `knowledge-base/out/kb.sqlite` path and the chunk count from Task 8. A count in the low hundreds means `KB_PATH` fell back to the fixture — fix that before spending the calls.

- [ ] **Step 2: Full Taglish run**

```bash
cd backend && uv run python eval/run_eval.py
```

- [ ] **Step 3: English spot-check**

```bash
cd backend && uv run python eval/run_eval.py --language en --subset 15
```

- [ ] **Step 4: Read the report before believing it**

Check in order: the baseline section reads F1 ≈ 0.618 (if it does not, the CSV drifted); the pipeline beats the baseline — **if it does not, that is the finding and it must be reported, not re-run until it looks better**; the per-message table shows the 12 chat-bait additions, which are where the pipeline should earn its result.

- [ ] **Step 5: Commit the results**

```bash
git add backend/eval/results/
git commit -m "test: eval results for the 85-message rebalanced set"
```

---

## Handoff

Nothing in this plan is pushed. When the branch is ready, `docs/eval-set-rebalance-spec` and the implementation commits merge to `main` per the daily-merge convention in `CLAUDE.md`.

The redeploy runbook's `chunk_count` check changes twice (Tasks 5 and 8). Confirm the final number is what `CLAUDE.md` says **before** the next deploy, or the verification step reports a false failure at the worst possible moment.
