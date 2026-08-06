# Elderly Scam Shield Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable SQL knowledge base of Philippine scam patterns — curated advisories, brand rebuttals, reporting contacts, and a real message corpus — that the RAG Agent retrieves over and the Advisor Agent reads by key.

**Architecture:** A `content/` tree of hand-curated YAML and verbatim fetched markdown is combined with the CC BY 4.0 scottleechua SMS corpus by a loader that writes `out/kb.sqlite` plus an equivalent Postgres seed for Supabase. Seven tables: a `sources` provenance registry, four typed content tables, a `message_examples` corpus table, and a single `kb_chunks` retrieval surface carrying an unpopulated pgvector column. A verification script gates the build on eval-set leakage, provenance completeness, and count reconciliation.

**Tech Stack:** Python 3.14 · SQLite 3.51 (build + verify) · PostgreSQL/pgvector (emitted, not executed) · pytest · requests · PyYAML · BeautifulSoup4

**Spec:** `docs/superpowers/specs/2026-08-05-scam-shield-knowledge-base-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.14.5.** Virtualenv at `knowledge-base/.venv`. No `uv`, no Docker, no local Postgres — all verified absent on 2026-08-06.
- **All commands run from the repo root** `/Users/nathanaelian/Documents/Uni/Term9/STSP001`.
- **Dataset URL, exact:** `https://raw.githubusercontent.com/scottleechua/data/main/spam-and-marketing-sms/text-messages.csv`
- **Dataset columns, exact:** `date-received`, `date-read`, `sender`, `category`, `text`
- **Dataset counts — verified 2026-08-06, treat as hard expectations:** 8,255 total · 1,907 usable (text not `<REDACTED>`) · spam 827 · ads 933 · gov 144 · notifs 3 · OTP 0 · coverage ends `2026-06-03 09:25:34`.
- **Eval holdout rule: exact-or-prefix on normalised text.** Not exact-hash. The eval CSV truncates at 400 chars; 5 rows hit the cap. Verified result: 55/55 eval rows matched, **140** dataset rows held out, retrievable pool **1,767**.
- **Verbatim means verbatim.** `brand_rebuttals.rebuttal_quote` and `advisories.body` are stored exactly as published. Never paraphrase, never reconstruct from memory, never substitute remembered text for a failed fetch.
- **A failed fetch is recorded and omitted, never invented.** `content/fetch_log.json` records every attempt with its status.
- **Every `kb_chunks` row has a resolvable `source_id`.** A chunk without provenance is a build failure.
- **No embeddings are generated.** `embedding` columns stay NULL. `scripts/embed.py` ships as a stub and is not run.
- **Hard negatives (`label = 'LEGIT'`) are never `retrievable = 1`.**
- **Licence:** the corpus is CC BY 4.0 and requires attribution. `ATTRIBUTION.md` is generated from the `sources` table, never hand-maintained.
- **Commit after every task.** Conventional-commit prefixes (`feat:`, `test:`, `docs:`, `chore:`).

---

## File Structure

```
knowledge-base/
  README.md                        what this is, how to rebuild it
  requirements.txt                 pinned deps
  .venv/                           gitignored
  schema/
    001_schema.sqlite.sql          build target
    001_schema.postgres.sql        Supabase target, pgvector-ready
  content/
    sources.yaml                   provenance registry (hand-authored + fetch-updated)
    lure_patterns.yaml             ~10 measured patterns, EN/TL triggers
    reporting_contacts.yaml        I-ARC 1326, PNP-ACG, BSP, NPC, NTC
    brand_rebuttals.yaml           4 brands, verbatim quotes from fetched pages
    advisories/*.md                verbatim fetched text + provenance front-matter
    fetch_log.json                 every fetch attempt and its outcome
  kb/
    __init__.py
    normalise.py                   text normalisation + exact-or-prefix holdout
    dataset.py                     corpus load + count reconciliation
    tagging.py                     scam_type, brand, has_url, taglish markers
    content.py                     YAML content loading + validation
    chunker.py                     rows -> kb_chunks
    db.py                          schema apply, insert, Postgres seed emit
  scripts/
    fetch_sources.py               live fetch
    build_kb.py                    orchestration
    verify_kb.py                   integrity gates
    embed.py                       provider-swappable stub, unrun
  tests/
    conftest.py
    fixtures/mini-corpus.csv
    fixtures/mini-eval.csv
    test_normalise.py
    test_dataset.py
    test_tagging.py
    test_content.py
    test_chunker.py
    test_db.py
    test_verify.py
  out/
    kb.sqlite                      gitignored
    kb_seed.postgres.sql           gitignored
  ATTRIBUTION.md                   generated
  HANDOFF-allen.md
```

**Responsibility split:** `kb/` is pure library code with no I/O side effects beyond reading its inputs — every module is unit-testable without network or database. `scripts/` holds the four entry points that do have side effects. Tests target `kb/`; the scripts are exercised by the end-to-end build in Task 9 and the gates in Task 10.

---

### Task 1: Scaffold, normalisation, and the eval-holdout rule

The holdout rule is the highest-risk logic in the project — getting it wrong silently invalidates the team's evaluation — so it is built first and in isolation.

**Files:**
- Create: `knowledge-base/requirements.txt`
- Create: `knowledge-base/kb/__init__.py`
- Create: `knowledge-base/kb/normalise.py`
- Create: `knowledge-base/tests/conftest.py`
- Create: `knowledge-base/tests/test_normalise.py`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `normalise_text(text: str) -> str`
  - `is_held_out(candidate: str, eval_norms: list[str]) -> bool`
  - `holdout_index(eval_texts: Iterable[str]) -> list[str]` — returns sorted normalised eval texts

- [ ] **Step 1: Create the virtualenv and dependency file**

```bash
cd /Users/nathanaelian/Documents/Uni/Term9/STSP001
python3 -m venv knowledge-base/.venv
knowledge-base/.venv/bin/python -m pip install --quiet --upgrade pip
```

`knowledge-base/requirements.txt`:

```
pytest>=8.0
requests>=2.32
PyYAML>=6.0
beautifulsoup4>=4.12
```

```bash
knowledge-base/.venv/bin/python -m pip install --quiet -r knowledge-base/requirements.txt
knowledge-base/.venv/bin/python -m pytest --version
```

Expected: a pytest version prints.

- [ ] **Step 2: Create `.gitignore`**

```
knowledge-base/.venv/
knowledge-base/out/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 3: Write the failing tests**

`knowledge-base/tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

`knowledge-base/tests/test_normalise.py`:

```python
from kb.normalise import normalise_text, is_held_out, holdout_index


def test_normalise_collapses_whitespace_and_lowercases():
    assert normalise_text("  BDO   ALERT\n\nYour  account ") == "bdo alert your account"


def test_normalise_strips_surrounding_punctuation():
    assert normalise_text("Verify here!!!") == "verify here"
    assert normalise_text("...Verify here") == "verify here"


def test_normalise_is_idempotent():
    once = normalise_text("  Hello   World!  ")
    assert normalise_text(once) == once


def test_exact_match_is_held_out():
    evals = holdout_index(["BDO ALERT Your account is on hold"])
    assert is_held_out("bdo alert your account is on hold", evals) is True


def test_prefix_match_is_held_out():
    # The eval CSV truncates at 400 chars; the dataset row is longer.
    truncated = "Get up to P2K Cashback with min. required spend at SM Appliance"
    full = truncated + " Center with your BDO Credit Card! T&Cs apply. DTI217131"
    evals = holdout_index([truncated])
    assert is_held_out(full, evals) is True


def test_suffix_match_is_not_held_out():
    evals = holdout_index(["Center with your BDO Credit Card"])
    assert is_held_out("Get up to P2K Center with your BDO Credit Card", evals) is False


def test_unrelated_message_is_not_held_out():
    evals = holdout_index(["BDO ALERT Your account is on hold"])
    assert is_held_out("Nice! You received a P20 voucher from Maya.", evals) is False


def test_empty_eval_text_never_matches():
    # A blank eval row must not hold out the entire corpus by prefix.
    evals = holdout_index(["", "   "])
    assert is_held_out("any message at all", evals) is False
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_normalise.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'kb'` or `ImportError`.

- [ ] **Step 5: Implement `kb/normalise.py`**

`knowledge-base/kb/__init__.py`: empty file.

`knowledge-base/kb/normalise.py`:

```python
"""Text normalisation and eval-set holdout matching.

The holdout rule is exact-or-prefix, not exact. The eval-set CSV truncates
message text at 400 characters; five rows hit that cap and are strict
prefixes of longer messages still present in the corpus. Exact matching
alone lets all five leak into the retrievable pool, which would let the
Detector retrieve the answers to its own evaluation.
"""

from __future__ import annotations

import re
from typing import Iterable

_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"^[\s.!?,;:\-–—'\"]+|[\s.!?,;:\-–—'\"]+$")

# Below this length a prefix match is too weak to be evidence of identity.
MIN_PREFIX_LEN = 24


def normalise_text(text: str) -> str:
    """Lowercase, collapse internal whitespace, strip surrounding punctuation."""
    if text is None:
        return ""
    collapsed = _WHITESPACE.sub(" ", str(text)).strip().lower()
    return _EDGE_PUNCT.sub("", collapsed)


def holdout_index(eval_texts: Iterable[str]) -> list[str]:
    """Normalised, de-duplicated, non-trivial eval texts, longest first."""
    seen = {normalise_text(t) for t in eval_texts}
    usable = {t for t in seen if len(t) >= MIN_PREFIX_LEN}
    return sorted(usable, key=len, reverse=True)


def is_held_out(candidate: str, eval_norms: list[str]) -> bool:
    """True if candidate equals, or begins with, any eval text."""
    norm = normalise_text(candidate)
    if not norm:
        return False
    return any(norm == e or norm.startswith(e) for e in eval_norms)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_normalise.py -v
```

Expected: 8 passed.

- [ ] **Step 7: Verify against the real data**

This is the measurement the spec's numbers came from. It must reproduce.

**Read both CSVs through a file handle opened with `newline=""`.** Messages in this corpus contain embedded newlines inside quoted fields. Reading via `urlopen(...).read().decode().splitlines()` splits those fields apart and silently loses 14 held-out rows, yielding 123 instead of 140. Every CSV read in this project uses a file handle for that reason.

```bash
knowledge-base/.venv/bin/python - <<'PY'
import csv, sys, urllib.request
from pathlib import Path
sys.path.insert(0, "knowledge-base")
from kb.normalise import holdout_index, is_held_out

URL = ("https://raw.githubusercontent.com/scottleechua/data/main/"
       "spam-and-marketing-sms/text-messages.csv")
cache = Path("knowledge-base/out/text-messages.csv")
cache.parent.mkdir(parents=True, exist_ok=True)
if not cache.exists():
    with urllib.request.urlopen(URL, timeout=120) as response:
        cache.write_bytes(response.read())

with open(cache, encoding="utf-8", newline="") as handle:
    rows = [r for r in csv.DictReader(handle) if "<REDACTED>" not in r["text"]]
with open("eval-set-candidate-55.csv", encoding="utf-8", newline="") as handle:
    evals = list(csv.DictReader(handle))

idx = holdout_index(e["text"] for e in evals)
matched = sum(1 for e in evals if is_held_out(e["text"], idx))
held = sum(1 for r in rows if is_held_out(r["text"], idx))
print(f"usable={len(rows)} eval_matched={matched}/{len(evals)} held_out={held} pool={len(rows)-held}")
PY
```

Expected, exactly: `usable=1907 eval_matched=55/55 held_out=140 pool=1767`

If these numbers differ, stop and report — do not proceed. The spec's figures and the deck depend on them.

- [ ] **Step 8: Commit**

```bash
git add .gitignore knowledge-base/requirements.txt knowledge-base/kb knowledge-base/tests
git commit -m "feat: add text normalisation and exact-or-prefix eval holdout"
```

---

### Task 2: Dataset loader with count reconciliation

**Files:**
- Create: `knowledge-base/kb/dataset.py`
- Create: `knowledge-base/tests/fixtures/mini-corpus.csv`
- Create: `knowledge-base/tests/test_dataset.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces:
  - `EXPECTED_COUNTS: dict[str, int]`
  - `DATASET_URL: str`
  - `fetch_dataset(cache_path: Path) -> Path` — downloads if absent, returns path
  - `load_rows(path: Path) -> list[dict]` — all 8,255 rows
  - `usable_rows(rows: list[dict]) -> list[dict]` — text not `<REDACTED>`
  - `reconcile(rows: list[dict]) -> dict` — `{"ok": bool, "actual": {...}, "expected": {...}, "deltas": {...}}`

- [ ] **Step 1: Write the fixture**

`knowledge-base/tests/fixtures/mini-corpus.csv`:

```csv
date-received,date-read,sender,category,text
2025-01-01 10:00:00,2025-01-01 10:05:00,redacted_business,notifs,<REDACTED>
2025-01-02 10:00:00,2025-01-02 10:05:00,redacted_business,OTP,<REDACTED>
2025-01-03 10:00:00,2025-01-03 10:05:00,masked_sender,spam,BDO ALERT Your account is on hold. Verify here: https://mybdo-fake.com
2025-01-04 10:00:00,2025-01-04 10:05:00,masked_sender,spam,Magdeposito ng 100P makakuha ng 117P libre 100k.cfd
2025-01-05 10:00:00,2025-01-05 10:05:00,masked_sender,ads,Nice! You received a P20 voucher from Maya. Tap Vouchers on the app.
2026-06-03 09:25:34,2026-06-03 09:30:00,masked_sender,gov,Beware of SCAMs. Report these on the NTC website or call the NTC Hotline 1682.
```

- [ ] **Step 2: Write the failing tests**

`knowledge-base/tests/test_dataset.py`:

```python
from pathlib import Path

from kb.dataset import EXPECTED_COUNTS, load_rows, usable_rows, reconcile

FIXTURE = Path(__file__).parent / "fixtures" / "mini-corpus.csv"


def test_load_rows_reads_all_rows_including_redacted():
    rows = load_rows(FIXTURE)
    assert len(rows) == 6
    assert set(rows[0].keys()) == {
        "date-received", "date-read", "sender", "category", "text",
    }


def test_usable_rows_excludes_redacted():
    rows = usable_rows(load_rows(FIXTURE))
    assert len(rows) == 4
    assert all("<REDACTED>" not in r["text"] for r in rows)


def test_expected_counts_match_the_verified_figures():
    assert EXPECTED_COUNTS == {
        "total": 8255,
        "usable": 1907,
        "spam": 827,
        "ads": 933,
        "gov": 144,
        "notifs": 3,
        "OTP": 0,
    }


def test_reconcile_reports_deltas_and_does_not_raise():
    result = reconcile(load_rows(FIXTURE))
    assert result["ok"] is False
    assert result["actual"]["total"] == 6
    assert result["actual"]["spam"] == 2
    assert result["deltas"]["total"] == 6 - 8255
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_dataset.py -v
```

Expected: FAIL — `No module named 'kb.dataset'`.

- [ ] **Step 4: Implement `kb/dataset.py`**

```python
"""Load the scottleechua PH spam/marketing SMS corpus and reconcile counts.

Licence: CC BY 4.0. Attribution is required and is emitted from the
`sources` table, not hand-maintained.

The expected counts below were verified against a fresh pull on 2026-08-06
and reproduce the figures in 2026-07-29-nian-dataset-findings.md exactly.
They appear on the team's deck, so a mismatch is surfaced rather than
silently accepted.
"""

from __future__ import annotations

import csv
import urllib.request
from pathlib import Path

DATASET_URL = (
    "https://raw.githubusercontent.com/scottleechua/data/main/"
    "spam-and-marketing-sms/text-messages.csv"
)

REDACTION_MARKER = "<REDACTED>"

EXPECTED_COUNTS = {
    "total": 8255,
    "usable": 1907,
    "spam": 827,
    "ads": 933,
    "gov": 144,
    "notifs": 3,
    "OTP": 0,
}


def fetch_dataset(cache_path: Path) -> Path:
    """Download the corpus unless it is already cached. Never re-downloads."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path
    with urllib.request.urlopen(DATASET_URL, timeout=120) as response:
        cache_path.write_bytes(response.read())
    return cache_path


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def usable_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if REDACTION_MARKER not in r["text"]]


def _counts(rows: list[dict]) -> dict:
    usable = usable_rows(rows)
    actual = {"total": len(rows), "usable": len(usable)}
    for category in ("spam", "ads", "gov", "notifs", "OTP"):
        actual[category] = sum(1 for r in usable if r["category"] == category)
    return actual


def reconcile(rows: list[dict]) -> dict:
    """Compare actual counts against the verified expectations."""
    actual = _counts(rows)
    deltas = {k: actual[k] - EXPECTED_COUNTS[k] for k in EXPECTED_COUNTS}
    return {
        "ok": all(d == 0 for d in deltas.values()),
        "actual": actual,
        "expected": dict(EXPECTED_COUNTS),
        "deltas": deltas,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_dataset.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Reconcile against the real corpus**

```bash
knowledge-base/.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "knowledge-base")
from pathlib import Path
from kb.dataset import fetch_dataset, load_rows, reconcile
p = fetch_dataset(Path("knowledge-base/out/text-messages.csv"))
r = reconcile(load_rows(p))
print("ok:", r["ok"]); print("actual:", r["actual"]); print("deltas:", r["deltas"])
PY
```

Expected: `ok: True` and all deltas `0`. If not, stop and report the deltas.

- [ ] **Step 7: Commit**

```bash
git add knowledge-base/kb/dataset.py knowledge-base/tests
git commit -m "feat: add corpus loader with verified count reconciliation"
```

---

### Task 3: Message tagging — scam type, brand, URL, Taglish markers

**Files:**
- Create: `knowledge-base/kb/tagging.py`
- Create: `knowledge-base/tests/test_tagging.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `TAGLISH_MARKERS: frozenset[str]`
  - `classify_scam_type(text: str) -> str | None`
  - `detect_brand(text: str) -> str | None`
  - `has_url(text: str) -> bool`
  - `count_taglish_markers(text: str) -> int`

**Honesty constraint carried into this task:** the exact keyword lists behind the 2026-07-29 figures (casino 465, bank 129, job 21, loan 16, package 14, prize 14, crypto 3) were never written down. These lists are a reconstruction, so the derived counts will not reproduce those figures exactly. The build **reports its computed counts** rather than asserting the recorded ones, and Task 9 records both side by side. Do not tune the keyword lists to hit the old numbers — that would be fitting the classifier to a figure rather than to the language.

- [ ] **Step 1: Write the failing tests**

`knowledge-base/tests/test_tagging.py`:

```python
from kb.tagging import (
    classify_scam_type,
    count_taglish_markers,
    detect_brand,
    has_url,
)


def test_detects_bank_impersonation():
    text = "BDO ALERT Your online access is suspended. To reactivate, register your device."
    assert classify_scam_type(text) == "bank-impersonation"


def test_detects_casino():
    text = "Magdeposito ng 100P, makakuha ng 117P na libre, 1X turnover 100k.cfd"
    assert classify_scam_type(text) == "casino"


def test_bank_impersonation_wins_over_casino_when_both_present():
    # "W19 Games, Official partner with GCash" is a casino ad naming a brand.
    # Brand mention alone must not make it bank impersonation.
    text = "W19 Games, Official partner with GCash, magdeposito para makakuha ng cashback!"
    assert classify_scam_type(text) == "casino"


def test_unmatched_returns_none():
    assert classify_scam_type("Kumusta ka na? Tara kain tayo bukas.") is None


def test_detect_brand_is_case_insensitive():
    assert detect_brand("Gcash. Account verification needed") == "gcash"
    assert detect_brand("[ BANCO DE ORO ] Your account") == "bdo"
    assert detect_brand("UNIONBANK FINAL WARNING") == "unionbank"
    assert detect_brand("#PAYMAYA Your voucher is expiring") == "maya"
    assert detect_brand("Kumusta ka na?") is None


def test_has_url_detects_bare_domains_and_schemes():
    assert has_url("Verify here: https://mybdo-fake.com") is True
    assert has_url("Visit centi.ai/GCashCarePH now") is True
    assert has_url("join us at 100k.cfd") is True
    assert has_url("Call us at 1326 for help") is False


def test_count_taglish_markers():
    assert count_taglish_markers("Magdeposito ka na ngayon para sa iyong bonus") >= 3
    assert count_taglish_markers("Your account has been suspended") == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_tagging.py -v
```

Expected: FAIL — `No module named 'kb.tagging'`.

- [ ] **Step 3: Implement `kb/tagging.py`**

```python
"""Keyword tagging for corpus messages.

These keyword lists are a reconstruction. The lists behind the 2026-07-29
figures were not recorded, so derived counts will differ from those figures.
Report computed counts; do not tune these lists to reproduce old numbers.

Ordering matters: casino is checked before bank-impersonation because
casino promos routinely name GCash or Maya as a deposit channel, and a
brand mention alone is not impersonation.
"""

from __future__ import annotations

import re

_CASINO = (
    "casino", "slot", "sl0t", "jackpot", "bonus", "deposit bonus", "magdeposito",
    "mag-deposito", "cashback", "turnover", "free spin", "libreng", "manalo",
    "panalo", "raffle", "recharge", "rehistro", "magparehistro", "welcome bonus",
    "red envelope", "fishing", "bet", "taya",
)
_BANK = (
    "verify your account", "account verification", "verify here", "update your",
    "registered mobile number", "online access", "account has been", "suspended",
    "deactivat", "restricted", "on hold", "on-hold", "reactivate", "final warning",
    "sim registration", "unrecognized attempts", "data breach", "otp",
)
_JOB = ("daily salary", "part time", "part-time", "job offer", "instructor", "task", "commission")
_LOAN = ("loan", "lowrate", "low rate", "cash loan", "avail 50k", "interested call")
_PACKAGE = ("parcel", "package", "delivery", "shipment", "customs", "unpaid balance", "on hold at")
_PRIZE = ("you won", "nanalo", "winner", "prize", "claim your", "lucky", "maswerteng")
_CRYPTO = ("crypto", "bitcoin", "usdt", "investment", "trading", "forex")

_BRANDS = {
    "gcash": ("gcash", "g-cash"),
    "unionbank": ("unionbank", "union bank", "unionbnk"),
    "bdo": ("bdo", "banco de oro"),
    "maya": ("paymaya", "maya"),
    "bpi": ("bpi", "bank of the philippine islands"),
    "metrobank": ("metrobank", "metro bank"),
}

# Ordered: first match wins.
_SCAM_TYPES = (
    ("casino", _CASINO),
    ("bank-impersonation", _BANK),
    ("job-task", _JOB),
    ("package", _PACKAGE),
    ("prize", _PRIZE),
    ("loan", _LOAN),
    ("crypto", _CRYPTO),
)

TAGLISH_MARKERS = frozenset({
    "ang", "ng", "mga", "sa", "na", "ay", "para", "ka", "mo", "ko", "ito",
    "iyong", "nang", "po", "at", "kayo", "namin", "natin", "ninyo", "siya",
    "hindi", "may", "meron", "wala", "dito", "ngayon", "lang", "din", "rin",
    "kung", "dahil", "upang", "tuwing", "gamit", "makakuha", "magparehistro",
    "magdeposito", "manalo", "panalo", "libre", "libreng", "bawat", "araw",
    "iyo", "kang", "naman", "pala", "yung", "mag", "pang", "tayo", "ako",
})

_URL = re.compile(
    r"(https?://\S+|www\.\S+|\b[a-z0-9][a-z0-9\-]{1,}\.(?:com|net|org|ph|io|ai|xyz|icu|"
    r"cfd|bid|tv|uk|de|eu|mom|world|link|online|shop|site|top|vip|win|fi|mx|by|cz|show|ac|"
    r"live|store)\b\S*)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-zA-ZñÑ]+")


def _lower(text: str) -> str:
    return (text or "").lower()


def classify_scam_type(text: str) -> str | None:
    low = _lower(text)
    for label, keywords in _SCAM_TYPES:
        if any(k in low for k in keywords):
            return label
    return None


def detect_brand(text: str) -> str | None:
    low = _lower(text)
    for brand, aliases in _BRANDS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", low):
                return brand
    return None


def has_url(text: str) -> bool:
    return bool(_URL.search(text or ""))


def count_taglish_markers(text: str) -> int:
    words = {w.lower() for w in _WORD.findall(text or "")}
    return len(words & TAGLISH_MARKERS)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_tagging.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Report computed distribution against the recorded figures**

```bash
knowledge-base/.venv/bin/python - <<'PY'
import sys, collections; sys.path.insert(0, "knowledge-base")
from pathlib import Path
from kb.dataset import fetch_dataset, load_rows, usable_rows
from kb.tagging import classify_scam_type, detect_brand, has_url, count_taglish_markers

rows = usable_rows(load_rows(fetch_dataset(Path("knowledge-base/out/text-messages.csv"))))
spam = [r for r in rows if r["category"] == "spam"]
types = collections.Counter(classify_scam_type(r["text"]) for r in spam)
brands = collections.Counter(b for r in spam if (b := detect_brand(r["text"])))
recorded = {"casino": 465, "bank-impersonation": 129, "job-task": 21,
            "loan": 16, "package": 14, "prize": 14, "crypto": 3}
print(f"{'type':22s} {'computed':>9s} {'recorded':>9s}")
for k in recorded:
    print(f"{k:22s} {types.get(k, 0):9d} {recorded[k]:9d}")
print(f"{'unmatched':22s} {types.get(None, 0):9d} {222:9d}")
print("brands:", dict(brands.most_common()))
print("has_url:", sum(has_url(r['text']) for r in spam), f"of {len(spam)}")
print("taglish>=3:", sum(count_taglish_markers(r['text']) >= 3 for r in spam))
PY
```

Expected: the table prints. Computed values will not equal recorded ones — that is expected and is the point of printing both. Record the output; Task 13 uses it. **Do not edit the keyword lists to close the gap.**

- [ ] **Step 6: Commit**

```bash
git add knowledge-base/kb/tagging.py knowledge-base/tests/test_tagging.py
git commit -m "feat: add keyword tagging for scam type, brand, URL, and Taglish markers"
```

---

### Task 4: Content model and hand-authored YAML

Authors the content that does not require fetching: the source registry skeleton, the measured lure patterns, and the reporting directory.

**Files:**
- Create: `knowledge-base/content/sources.yaml`
- Create: `knowledge-base/content/lure_patterns.yaml`
- Create: `knowledge-base/content/reporting_contacts.yaml`
- Create: `knowledge-base/kb/content.py`
- Create: `knowledge-base/tests/test_content.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `load_sources(root: Path) -> list[dict]`
  - `load_lure_patterns(root: Path) -> list[dict]`
  - `load_reporting_contacts(root: Path) -> list[dict]`
  - `load_brand_rebuttals(root: Path) -> list[dict]` — returns `[]` if the file is absent (Task 6 creates it)
  - `load_advisories(root: Path) -> list[dict]` — parses `content/advisories/*.md` front-matter; `[]` if the directory is absent
  - `validate_content(bundle: dict) -> list[str]` — returns human-readable problems, empty when clean

- [ ] **Step 1: Author `content/reporting_contacts.yaml`**

All values below come from `2026-07-29-plan3-scam-shield-datasets.md` and the corpus itself (NTC 1682 appears verbatim in a `gov` message).

```yaml
- contact_id: i-arc-1326
  organisation: Inter-Agency Response Center (I-ARC)
  hotline: "1326"
  email: ""
  url: https://www.cybersecurity.ph/cybercrime-reporting/
  covers: >-
    Joint DICT / CICC / NPC / NTC reporting hotline for cybercrime and online
    scams. The single number to give first.
  priority: 1
  source_id: cybersecurity-ph-reporting

- contact_id: pnp-acg
  organisation: PNP Anti-Cybercrime Group
  hotline: ""
  email: ""
  url: https://acg.pnp.gov.ph/
  covers: Criminal complaints for cybercrime, including online fraud and smishing.
  priority: 2
  source_id: pnp-acg-advisories

- contact_id: bsp-consumer
  organisation: Bangko Sentral ng Pilipinas — Consumer Assistance
  hotline: "(+632) 8811-1277"
  email: consumeraffairs@bsp.gov.ph
  url: https://www.bsp.gov.ph/
  covers: Complaints about banks and BSP-supervised financial institutions.
  priority: 3
  source_id: bsp-consumer-advisories

- contact_id: npc
  organisation: National Privacy Commission
  hotline: ""
  email: ""
  url: https://privacy.gov.ph/
  covers: Personal-data misuse and breach-driven scams.
  priority: 4
  source_id: npc-advisories

- contact_id: ntc-1682
  organisation: National Telecommunications Commission
  hotline: "1682"
  email: ""
  url: https://ntc.gov.ph/
  covers: >-
    Reporting scam text messages to the telco regulator. Cited verbatim in
    NTC's own public service messages in the corpus.
  priority: 5
  source_id: ntc-public-advisory
```

- [ ] **Step 2: Author `content/lure_patterns.yaml`**

Bank-impersonation shares come from the 2026-07-29 analysis of the 129 on-target messages; scam-type counts come from the 827-message distribution.

```yaml
- pattern_id: verify-update-account
  name: Verify or update your account
  scam_type: bank-impersonation
  measured_share: 0.34
  measured_count: 44
  description: >-
    Claims the recipient must verify or update their account details, usually
    via a link, or lose access. The most common bank-impersonation lure.
  red_flags: >-
    Asks you to verify an account by SMS link; no bank or e-wallet does this.
    Link domain is not the bank's official domain. Often a URL shortener.
  triggers_en: "verify your account; account verification; update your account; verify here; kindly visit"
  triggers_tl: "i-verify ang iyong account; kailangan i-update; magparehistro; pakiverify"
  source_id: scottleechua-ph-sms

- pattern_id: account-suspended
  name: Account suspended or restricted
  scam_type: bank-impersonation
  measured_share: 0.24
  measured_count: 31
  description: >-
    States the account is already suspended, restricted, disabled, or on hold,
    creating alarm before the recipient can check.
  red_flags: >-
    Alarming status claim delivered by SMS rather than in the app. Real
    suspensions appear when you log in, not as a text with a link.
  triggers_en: "temporarily disabled; account suspended; restricted; on hold; deactivated; final warning"
  triggers_tl: "naka-hold ang account; sinuspinde; hindi na magagamit; huling babala"
  source_id: scottleechua-ph-sms

- pattern_id: urgency-deadline
  name: Urgency deadline
  scam_type: bank-impersonation
  measured_share: 0.17
  measured_count: 22
  description: >-
    Attaches a short deadline — 24 hours, tomorrow, immediately — so the
    recipient acts before verifying through an official channel.
  red_flags: >-
    A countdown is a pressure tactic. Any genuine issue will still be there
    after you call the official hotline.
  triggers_en: "within 24 hours; expires today; immediately; avoid deactivation tomorrow; act now"
  triggers_tl: "ngayon din; bukas na; agad; bago mag-expire; huwag palampasin"
  source_id: scottleechua-ph-sms

- pattern_id: click-this-link
  name: Click this link
  scam_type: bank-impersonation
  measured_share: 0.17
  measured_count: 22
  description: >-
    The payload is the link itself, very often a shortener that hides the
    destination domain.
  red_flags: >-
    Shortened links hide where they go and do not appear on blocklists.
    Two-thirds of scam messages carry no link at all, so a link is a strong
    signal but its absence proves nothing.
  triggers_en: "click here; visit; proceed to; tap this link; continue here"
  triggers_tl: "pindutin dito; bisitahin; pumunta dito; i-click"
  source_id: scottleechua-ph-sms

- pattern_id: casino-promo
  name: Online casino or gambling promotion
  scam_type: casino
  measured_share: 0.562
  measured_count: 465
  description: >-
    Deposit-bonus, cashback, free-spin, or jackpot promotions for unlicensed
    online gambling sites. The single largest category in the corpus and the
    most likely thing an elderly user will actually paste.
  red_flags: >-
    Guaranteed winnings, free money for registering, and throwaway domains.
    Often names GCash or Maya as a deposit channel, which is not endorsement.
  triggers_en: "free bonus; deposit bonus; cashback; jackpot; slot; welcome gift; turnover"
  triggers_tl: "magdeposito; makakuha ng libre; manalo; panalo; magparehistro; recharge; taya"
  source_id: scottleechua-ph-sms

- pattern_id: job-task-scam
  name: Job or task scam
  scam_type: job-task
  measured_share: 0.025
  measured_count: 21
  description: >-
    Offers easy daily earnings for simple online tasks, then asks for an
    up-front deposit or personal details.
  red_flags: "Unsolicited job offer, guaranteed daily rate, contact via personal messaging app."
  triggers_en: "daily salary; part time; easy income; contact the instructor; commission"
  triggers_tl: "araw-araw na kita; madaling trabaho; part time; kumita agad"
  source_id: scottleechua-ph-sms

- pattern_id: loan-offer
  name: Unsolicited loan offer
  scam_type: loan
  measured_share: 0.019
  measured_count: 16
  description: Offers fast cash at a low rate, typically with a personal mobile number as contact.
  red_flags: "Legitimate lenders do not solicit by SMS from personal numbers or ask for advance fees."
  triggers_en: "avail 50k; low rate; secured process; interested call; cash loan"
  triggers_tl: "mabilis na cash; mababang interes; text mo lang ako"
  source_id: scottleechua-ph-sms

- pattern_id: package-delivery
  name: Package or delivery problem
  scam_type: package
  measured_share: 0.017
  measured_count: 14
  description: >-
    Claims a parcel is held pending an unpaid fee or address confirmation.
    Small in this corpus, but it is one of the two scenarios in the team's
    own UI prototype.
  red_flags: "Unexpected parcel, small fee demanded by link, courier not named or misspelled."
  triggers_en: "parcel on hold; unpaid balance; delivery failed; confirm your address; customs fee"
  triggers_tl: "naka-hold ang parcel; may bayad pa; kumpirmahin ang address"
  source_id: scottleechua-ph-sms

- pattern_id: prize-raffle
  name: Prize or raffle win
  scam_type: prize
  measured_share: 0.017
  measured_count: 14
  description: Tells the recipient they have won something they never entered.
  red_flags: "You cannot win a raffle you did not enter. Claim links harvest credentials."
  triggers_en: "you won; congratulations; claim your prize; lucky winner"
  triggers_tl: "nanalo ka; maswerteng; i-claim mo na; congrats"
  source_id: scottleechua-ph-sms

- pattern_id: crypto-investment
  name: Crypto or investment offer
  scam_type: crypto
  measured_share: 0.004
  measured_count: 3
  description: >-
    Investment or trading offers promising outsized returns. Near-absent in
    SMS despite being prominent in general scam taxonomies — included so the
    KB can say it is rare rather than being silent about it.
  red_flags: "Guaranteed returns, time-limited entry, unregistered platform."
  triggers_en: "guaranteed returns; trading signals; investment opportunity; crypto"
  triggers_tl: "siguradong kita; puhunan; mag-invest ka na"
  source_id: scottleechua-ph-sms
```

- [ ] **Step 3: Author `content/sources.yaml`**

`retrieved_at` is left blank for fetched sources; Task 5 fills it from `fetch_log.json`. Sources not requiring a fetch carry their date now.

```yaml
- source_id: scottleechua-ph-sms
  name: PH Spam and Marketing SMS (with timestamps)
  organisation: Scott Lee Chua
  url: https://github.com/scottleechua/data/tree/main/spam-and-marketing-sms
  retrieved_at: "2026-08-06"
  licence: CC BY 4.0
  attribution: >-
    Chua, Scott Lee. "Spam and marketing SMS with timestamps." Available at
    https://github.com/scottleechua/data. Licensed under CC BY 4.0.
  notes: >-
    8,255 messages; 1,907 with usable text after the author's privacy
    redaction. OTP and notifs are effectively fully redacted.

- source_id: bsp-consumer-advisories
  name: BSP consumer advisories
  organisation: Bangko Sentral ng Pilipinas
  url: https://www.bsp.gov.ph/
  retrieved_at: ""
  licence: public advisory
  attribution: Bangko Sentral ng Pilipinas consumer advisories.
  notes: ""

- source_id: pnp-acg-advisories
  name: PNP Anti-Cybercrime Group advisories
  organisation: Philippine National Police
  url: https://acg.pnp.gov.ph/
  retrieved_at: ""
  licence: public advisory
  attribution: PNP Anti-Cybercrime Group public advisories.
  notes: ""

- source_id: npc-advisories
  name: NPC privacy advisories
  organisation: National Privacy Commission
  url: https://privacy.gov.ph/
  retrieved_at: ""
  licence: public advisory
  attribution: National Privacy Commission advisories.
  notes: ""

- source_id: cybersecurity-ph-reporting
  name: Cybercrime reporting guide
  organisation: cybersecurity.ph
  url: https://www.cybersecurity.ph/cybercrime-reporting/
  retrieved_at: ""
  licence: public guidance
  attribution: cybersecurity.ph cybercrime reporting guide.
  notes: Primary source for the I-ARC 1326 hotline.

- source_id: scamwatch-pilipinas
  name: ScamWatch Pilipinas
  organisation: ScamWatch Pilipinas
  url: https://scamwatchpilipinas.com/
  retrieved_at: ""
  licence: public advisory
  attribution: ScamWatch Pilipinas.
  notes: NGO source; best for fresh patterns.

- source_id: ntc-public-advisory
  name: NTC public scam advisory
  organisation: National Telecommunications Commission
  url: https://ntc.gov.ph/
  retrieved_at: "2026-08-06"
  licence: public advisory
  attribution: National Telecommunications Commission public advisories.
  notes: >-
    Hotline 1682 is quoted verbatim in NTC public service messages present in
    the corpus (see gov-category messages).

- source_id: gcash-fraud-advisory
  name: GCash security advisories
  organisation: GCash (Mynt)
  url: https://www.gcash.com/
  retrieved_at: ""
  licence: brand advisory
  attribution: GCash official security guidance.
  notes: ""

- source_id: unionbank-fraud-advisory
  name: UnionBank fraud advisories
  organisation: UnionBank of the Philippines
  url: https://www.unionbankph.com/
  retrieved_at: ""
  licence: brand advisory
  attribution: UnionBank of the Philippines official fraud guidance.
  notes: ""

- source_id: bdo-fraud-advisory
  name: BDO security advisories
  organisation: BDO Unibank
  url: https://www.bdo.com.ph/
  retrieved_at: ""
  licence: brand advisory
  attribution: BDO Unibank official security guidance.
  notes: ""

- source_id: maya-fraud-advisory
  name: Maya security advisories
  organisation: Maya Philippines
  url: https://www.maya.ph/help
  retrieved_at: ""
  licence: brand advisory
  attribution: Maya Philippines official security guidance.
  notes: ""
```

- [ ] **Step 4: Write the failing tests**

`knowledge-base/tests/test_content.py`:

```python
from pathlib import Path

from kb.content import (
    load_advisories,
    load_brand_rebuttals,
    load_lure_patterns,
    load_reporting_contacts,
    load_sources,
    validate_content,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sources_load_with_required_fields():
    sources = load_sources(ROOT)
    assert len(sources) >= 11
    ids = {s["source_id"] for s in sources}
    assert "scottleechua-ph-sms" in ids
    assert "i-arc" not in ids  # contacts are not sources
    for s in sources:
        assert s["url"].startswith("http")
        assert s["licence"]
        assert s["attribution"]


def test_lure_patterns_carry_measured_figures_and_bilingual_triggers():
    patterns = load_lure_patterns(ROOT)
    assert len(patterns) >= 10
    for p in patterns:
        assert p["triggers_en"].strip()
        assert p["triggers_tl"].strip()
        assert 0.0 < p["measured_share"] <= 1.0
        assert p["measured_count"] > 0
        # lure_patterns.source_id is NOT NULL in the schema; a missing value
        # here fails at insert time in Task 9 rather than here, so catch it now.
        assert p["source_id"] == "scottleechua-ph-sms"


def test_casino_is_the_largest_pattern():
    patterns = {p["pattern_id"]: p for p in load_lure_patterns(ROOT)}
    assert patterns["casino-promo"]["measured_count"] == 465


def test_reporting_contacts_lead_with_iarc():
    contacts = sorted(load_reporting_contacts(ROOT), key=lambda c: c["priority"])
    assert contacts[0]["contact_id"] == "i-arc-1326"
    assert contacts[0]["hotline"] == "1326"


def test_missing_optional_files_return_empty_not_error():
    assert load_brand_rebuttals(Path("/nonexistent")) == []
    assert load_advisories(Path("/nonexistent")) == []


def test_validate_flags_a_contact_pointing_at_an_unknown_source():
    bundle = {
        "sources": [{"source_id": "known", "url": "https://x", "licence": "p",
                     "attribution": "a", "retrieved_at": "2026-08-06"}],
        "lure_patterns": [],
        "reporting_contacts": [{"contact_id": "c", "source_id": "ghost", "priority": 1,
                                "organisation": "o", "hotline": "1", "email": "",
                                "url": "https://x", "covers": "c"}],
        "brand_rebuttals": [],
        "advisories": [],
    }
    problems = validate_content(bundle)
    assert any("ghost" in p for p in problems)


def test_validate_passes_on_the_real_content():
    bundle = {
        "sources": load_sources(ROOT),
        "lure_patterns": load_lure_patterns(ROOT),
        "reporting_contacts": load_reporting_contacts(ROOT),
        "brand_rebuttals": load_brand_rebuttals(ROOT),
        "advisories": load_advisories(ROOT),
    }
    assert validate_content(bundle) == []
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_content.py -v
```

Expected: FAIL — `No module named 'kb.content'`.

- [ ] **Step 6: Implement `kb/content.py`**

```python
"""Load and validate the hand-curated content tree."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or []


def load_sources(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "sources.yaml")


def load_lure_patterns(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "lure_patterns.yaml")


def load_reporting_contacts(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "reporting_contacts.yaml")


def load_brand_rebuttals(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "brand_rebuttals.yaml")


def load_advisories(root: Path) -> list[dict]:
    """Parse content/advisories/*.md — YAML front-matter plus verbatim body."""
    directory = root / "content" / "advisories"
    if not directory.exists():
        return []
    advisories = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{path} is missing YAML front-matter")
        _, front, body = text.split("---", 2)
        meta = yaml.safe_load(front) or {}
        meta["body"] = body.strip()
        meta.setdefault("advisory_id", path.stem)
        advisories.append(meta)
    return advisories


def validate_content(bundle: dict) -> list[str]:
    """Return human-readable problems. Empty list means clean."""
    problems: list[str] = []
    source_ids = {s["source_id"] for s in bundle["sources"]}

    for source in bundle["sources"]:
        for field in ("url", "licence", "attribution"):
            if not str(source.get(field, "")).strip():
                problems.append(f"source {source['source_id']}: empty {field}")

    def check_ref(kind: str, key: str, rows: list[dict]) -> None:
        for row in rows:
            ref = row.get("source_id")
            if ref not in source_ids:
                problems.append(f"{kind} {row.get(key)}: unknown source_id {ref!r}")

    check_ref("contact", "contact_id", bundle["reporting_contacts"])
    check_ref("rebuttal", "brand_id", bundle["brand_rebuttals"])
    check_ref("advisory", "advisory_id", bundle["advisories"])
    check_ref("pattern", "pattern_id", bundle["lure_patterns"])

    for pattern in bundle["lure_patterns"]:
        if not str(pattern.get("triggers_tl", "")).strip():
            problems.append(f"pattern {pattern.get('pattern_id')}: empty triggers_tl")
        if not str(pattern.get("triggers_en", "")).strip():
            problems.append(f"pattern {pattern.get('pattern_id')}: empty triggers_en")

    for rebuttal in bundle["brand_rebuttals"]:
        for field in ("rebuttal_quote", "official_url"):
            if not str(rebuttal.get(field, "")).strip():
                problems.append(f"rebuttal {rebuttal.get('brand_id')}: empty {field}")

    return problems
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_content.py -v
```

Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add knowledge-base/content knowledge-base/kb/content.py knowledge-base/tests/test_content.py
git commit -m "feat: add curated lure patterns, reporting contacts, and source registry"
```

---

### Task 5: Live source fetcher

**Files:**
- Create: `knowledge-base/scripts/__init__.py` (empty — makes `scripts` importable by Task 6 and the Task 10 tests)
- Create: `knowledge-base/scripts/fetch_sources.py`
- Create: `knowledge-base/content/fetch_log.json` (generated)
- Create: `knowledge-base/content/advisories/*.md` (generated)

**Interfaces:**
- Consumes: `load_sources` from Task 4
- Produces: `content/fetch_log.json` with `{source_id: {url, status, http_status, bytes, fetched_at, error}}`, and one `advisories/<source_id>.md` per successful fetch with front-matter keys `advisory_id`, `title`, `language`, `source_id`, `published_at`

- [ ] **Step 1: Implement the fetcher**

`knowledge-base/scripts/fetch_sources.py`:

```python
"""Fetch live advisory sources to disk. Failures are recorded, never invented.

Run from the repo root:
    knowledge-base/.venv/bin/python knowledge-base/scripts/fetch_sources.py

Fetched markdown is committed, so a later build never depends on a site
still being reachable.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kb.content import load_sources  # noqa: E402

HEADERS = {"User-Agent": "STSP001-capstone-kb/1.0 (academic research; contact via GitHub)"}
TIMEOUT = 30
MIN_USEFUL_CHARS = 200

# Sources fetched as advisory documents. The corpus source is downloaded
# separately by kb.dataset, and is excluded here.
SKIP = {"scottleechua-ph-sms"}


def extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    body = "\n".join(line for line in lines if line)
    return title, body


def main() -> int:
    sources = [s for s in load_sources(ROOT) if s["source_id"] not in SKIP]
    out_dir = ROOT / "content" / "advisories"
    out_dir.mkdir(parents=True, exist_ok=True)
    log: dict[str, dict] = {}
    today = date.today().isoformat()

    for source in sources:
        sid, url = source["source_id"], source["url"]
        entry = {
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "failed",
            "http_status": None,
            "bytes": 0,
            "error": "",
        }
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            entry["http_status"] = response.status_code
            response.raise_for_status()
            title, body = extract_text(response.text)
            entry["bytes"] = len(body)
            if len(body) < MIN_USEFUL_CHARS:
                entry["status"] = "empty"
                entry["error"] = f"only {len(body)} chars of text extracted"
            else:
                front = {
                    "advisory_id": sid,
                    "title": title or source["name"],
                    "language": "en",
                    "published_at": None,
                    "source_id": sid,
                    "retrieved_at": today,
                    "retrieved_from": url,
                }
                doc = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + body + "\n"
                (out_dir / f"{sid}.md").write_text(doc, encoding="utf-8")
                entry["status"] = "ok"
        except Exception as exc:  # noqa: BLE001 - every failure mode is recorded, not raised
            entry["error"] = f"{type(exc).__name__}: {exc}"
        log[sid] = entry
        print(f"{entry['status']:>7}  {sid:32s} {entry['http_status']} {entry['bytes']}b {entry['error']}")

    (ROOT / "content" / "fetch_log.json").write_text(
        json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    ok = sum(1 for e in log.values() if e["status"] == "ok")
    print(f"\n{ok} of {len(log)} sources fetched. Failures are omitted from the KB, not invented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the fetcher**

```bash
knowledge-base/.venv/bin/python knowledge-base/scripts/fetch_sources.py
```

Expected: a per-source status line, then a summary. **Most of the high-value sources will fail**, and this is not a bug in the fetcher.

Probed from this machine on 2026-08-06 with a browser User-Agent:

| URL | Status |
|---|---|
| `https://www.cybersecurity.ph/cybercrime-reporting/` | **200** |
| `https://scamwatchpilipinas.com/` | **200** |
| `https://www.maya.ph/help` | **200** |
| `https://www.gcash.com/` | **200** |
| `https://privacy.gov.ph/` | **200** |
| `https://privacy.gov.ph/advisories/` | 403 |
| `https://help.gcash.com/hc/en-us` | 403 |
| `https://www.unionbankph.com/` | 403 |
| `https://acg.pnp.gov.ph/` | 403 |
| `https://ntc.gov.ph/` | 403 |
| `https://www.bdo.com.ph/` | connection failed |
| `https://www.bsp.gov.ph/SitePages/InformationandAdvisories/Advisories.aspx` | 404 |

403 here is bot protection, not absence — these pages load normally in a real browser. Record the failures and move to the next step; do not add retry loops, rotate User-Agents, or otherwise try to defeat the protection.

- [ ] **Step 3: Retry blocked sources in a real browser**

For every source whose status is not `ok`, open the page in Chrome via the `claude-in-chrome` tools, read the rendered text, and save it as an advisory file by hand in the same format `fetch_sources.py` writes:

```
---
advisory_id: <source_id>
title: <page title>
language: en
published_at: null
source_id: <source_id>
retrieved_at: 2026-08-06
retrieved_from: <the exact URL loaded>
---

<verbatim page text>
```

Then set that source's `fetch_log.json` entry to `{"status": "ok-browser", ...}` with a note recording that it was captured through the browser rather than by script. The distinction matters for reproducibility: a future rebuild will not reproduce these automatically.

This step needs Nian's Chrome and per-site permission in the extension. If the browser route is unavailable or a page still cannot be read, the source is **omitted**. Never reconstruct advisory text from memory.

Also correct any URL that returned 404 — `sources.yaml` currently points BSP at a path that no longer exists. Find the live advisories page, update the YAML, and note the change.

- [ ] **Step 4: Update `retrieved_at` in `sources.yaml` from the log**

```bash
knowledge-base/.venv/bin/python - <<'PY'
import json, sys, yaml; sys.path.insert(0, "knowledge-base")
from pathlib import Path
root = Path("knowledge-base")
log = json.loads((root / "content" / "fetch_log.json").read_text())
path = root / "content" / "sources.yaml"
sources = yaml.safe_load(path.read_text(encoding="utf-8"))
for s in sources:
    entry = log.get(s["source_id"])
    if entry and entry["status"] == "ok":
        s["retrieved_at"] = entry["fetched_at"][:10]
path.write_text(yaml.safe_dump(sources, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")
print("updated:", [s["source_id"] for s in sources if s["retrieved_at"]])
PY
```

- [ ] **Step 5: Inspect what actually came back**

```bash
ls -la knowledge-base/content/advisories/
knowledge-base/.venv/bin/python -c "import json;d=json.load(open('knowledge-base/content/fetch_log.json'));[print(f\"{v['status']:>7} {k}\") for k,v in sorted(d.items())]"
```

Read at least two of the fetched markdown files. If a file is navigation boilerplate rather than advisory text, delete it and set that source's `fetch_log` status to `empty` by hand with a note — a page of menu links is worse than no page, because it will be chunked and retrieved.

- [ ] **Step 6: Commit**

```bash
git add knowledge-base/scripts knowledge-base/content
git commit -m "feat: fetch live PH advisory sources with a recorded fetch log"
```

---

### Task 6: Curate brand rebuttals from fetched sources

The single highest-value table. Four brands, ranked by measured frequency: GCash (39), UnionBank (29), BDO (24), Maya (9).

**Files:**
- Create: `knowledge-base/content/brand_rebuttals.yaml`
- Modify: `knowledge-base/content/sources.yaml` (only if a rebuttal is sourced from a URL not yet registered)

**Interfaces:**
- Consumes: `content/advisories/*.md` and `fetch_log.json` from Task 5
- Produces: `content/brand_rebuttals.yaml` with keys `brand_id`, `brand_name`, `rebuttal_quote`, `official_hotline`, `official_url`, `official_channels`, `measured_frequency`, `source_id`

- [ ] **Step 1: Locate the rebuttal text for each brand**

For each of `gcash`, `unionbank`, `bdo`, `maya`, search the fetched advisories for the brand's own "we will never ask…" statement and its official hotline:

```bash
grep -ri -n -E "never (ask|request)|will not ask|official hotline|customer service|report.{0,20}fraud" \
  knowledge-base/content/advisories/ | head -40
```

If the fetched page does not contain the statement, try the brand's specific security page. Candidates, with their probed status from 2026-08-06:

| Brand | Candidate URLs | Probed |
|---|---|---|
| GCash | `https://www.gcash.com/` · `https://help.gcash.com/hc/en-us` | 200 · 403 |
| Maya | `https://www.maya.ph/help` | 200 |
| UnionBank | `https://www.unionbankph.com/` · `/fraud-awareness` · `/security` | 403 |
| BDO | `https://www.bdo.com.ph/` | connection failed |

Script-fetch a candidate:

```bash
knowledge-base/.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "knowledge-base")
import requests
from scripts.fetch_sources import extract_text, HEADERS

url = "https://www.gcash.com/"   # swap in the candidate you are checking
r = requests.get(url, headers=HEADERS, timeout=30)
title, body = extract_text(r.text)
print(r.status_code, len(body), "chars"); print(title); print(body[:3000])
PY
```

For the 403 and connection-failed brands, use the browser route from Task 5 Step 3 — those pages load fine for a human. **UnionBank and BDO are brands 2 and 3 by measured frequency (29 and 24 messages), so getting them is worth the browser detour.**

**Absolute rule for this step:** if a brand's statement cannot be found on a page you actually fetched, that brand gets **no row**. Do not write a plausible-sounding rebuttal from memory. An invented quote attributed to a bank is the single worst failure this KB can contain, and it is exactly the kind of thing a mentor will spot-check.

- [ ] **Step 2: Author `content/brand_rebuttals.yaml`**

Shape, using the measured frequencies as given. Fill `rebuttal_quote`, `official_hotline`, and `official_url` **only** from fetched text; delete any brand block you could not source.

```yaml
- brand_id: gcash
  brand_name: GCash
  rebuttal_quote: "<verbatim from the fetched GCash page>"
  official_hotline: "<verbatim>"
  official_url: "<the exact URL fetched>"
  official_channels: "<verbatim, e.g. in-app Help Center only>"
  measured_frequency: 39
  source_id: gcash-fraud-advisory

- brand_id: unionbank
  brand_name: UnionBank of the Philippines
  rebuttal_quote: "<verbatim>"
  official_hotline: "<verbatim>"
  official_url: "<the exact URL fetched>"
  official_channels: "<verbatim>"
  measured_frequency: 29
  source_id: unionbank-fraud-advisory

- brand_id: bdo
  brand_name: BDO Unibank
  rebuttal_quote: "<verbatim>"
  official_hotline: "<verbatim>"
  official_url: "<the exact URL fetched>"
  official_channels: "<verbatim>"
  measured_frequency: 24
  source_id: bdo-fraud-advisory

- brand_id: maya
  brand_name: Maya
  rebuttal_quote: "<verbatim>"
  official_hotline: "<verbatim>"
  official_url: "<the exact URL fetched>"
  official_channels: "<verbatim>"
  measured_frequency: 9
  source_id: maya-fraud-advisory
```

BPI and Metrobank are deliberately excluded — 1 and 0 messages respectively in the corpus, against the June scope that named them. Do not add them.

- [ ] **Step 3: Verify content validation still passes**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_content.py -v
```

Expected: 7 passed. `validate_content` rejects any rebuttal with an empty `rebuttal_quote` or `official_url`, so a half-filled row fails here rather than reaching the database.

- [ ] **Step 4: Record which brands were sourced**

```bash
knowledge-base/.venv/bin/python -c "
import sys; sys.path.insert(0,'knowledge-base')
from pathlib import Path
from kb.content import load_brand_rebuttals
rows = load_brand_rebuttals(Path('knowledge-base'))
print(f'{len(rows)} of 4 target brands sourced:', [r['brand_id'] for r in rows])
"
```

Note the result. If fewer than 4, that gap goes in the Task 13 summary and the Task 12 handoff as an explicit open item.

- [ ] **Step 5: Commit**

```bash
git add knowledge-base/content
git commit -m "feat: add verbatim brand rebuttals for the measured impersonated brands"
```

---

### Task 7: Chunker

**Files:**
- Create: `knowledge-base/kb/chunker.py`
- Create: `knowledge-base/tests/test_chunker.py`

**Interfaces:**
- Consumes: content loaders (Task 4), `count_taglish_markers` (Task 3)
- Produces:
  - `MAX_CHUNK_CHARS: int`
  - `split_advisory(body: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]`
  - `build_chunks(bundle: dict, messages: list[dict]) -> list[dict]` — rows with keys `chunk_id`, `text`, `parent_type`, `parent_id`, `source_id`, `keywords_en`, `keywords_tl`

- [ ] **Step 1: Write the failing tests**

`knowledge-base/tests/test_chunker.py`:

```python
from kb.chunker import MAX_CHUNK_CHARS, build_chunks, split_advisory


def test_short_advisory_is_one_chunk():
    assert split_advisory("A short advisory.") == ["A short advisory."]


def test_long_advisory_splits_on_paragraph_boundaries():
    para = "x" * 1200
    chunks = split_advisory(f"{para}\n\n{para}")
    assert len(chunks) == 2
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)


def test_oversized_paragraph_is_hard_split():
    chunks = split_advisory("y" * (MAX_CHUNK_CHARS * 2 + 50))
    assert len(chunks) == 3
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)


def _bundle():
    return {
        "sources": [{"source_id": "s1"}],
        "lure_patterns": [{
            "pattern_id": "p1", "name": "Verify", "description": "d", "red_flags": "r",
            "scam_type": "bank-impersonation", "measured_share": 0.34, "measured_count": 44,
            "triggers_en": "verify here", "triggers_tl": "i-verify",
            "source_id": "s1",
        }],
        "reporting_contacts": [],
        "brand_rebuttals": [{
            "brand_id": "gcash", "brand_name": "GCash", "rebuttal_quote": "We never ask.",
            "official_hotline": "2882", "official_url": "https://x", "official_channels": "app",
            "measured_frequency": 39, "source_id": "s1",
        }],
        "advisories": [{"advisory_id": "a1", "title": "T", "body": "Body text.", "source_id": "s1"}],
    }


def test_build_chunks_covers_every_parent_type():
    messages = [{
        "message_id": "m1", "text": "Magdeposito ka na ngayon sa link na ito",
        "retrievable": 1, "source_id": "s1",
    }]
    chunks = build_chunks(_bundle(), messages)
    assert {c["parent_type"] for c in chunks} == {
        "lure_pattern", "brand_rebuttal", "advisory", "message_example",
    }


def test_non_retrievable_messages_are_not_chunked():
    messages = [{"message_id": "m1", "text": "held out", "retrievable": 0, "source_id": "s1"}]
    chunks = build_chunks(_bundle(), messages)
    assert not any(c["parent_type"] == "message_example" for c in chunks)


def test_every_chunk_has_source_and_bilingual_keywords():
    messages = [{"message_id": "m1", "text": "Magparehistro ka na para makakuha ng bonus",
                 "retrievable": 1, "source_id": "s1"}]
    for chunk in build_chunks(_bundle(), messages):
        assert chunk["source_id"] == "s1"
        assert chunk["keywords_en"].strip() or chunk["keywords_tl"].strip()
        assert chunk["chunk_id"]


def test_pattern_chunk_carries_both_trigger_languages():
    chunk = next(c for c in build_chunks(_bundle(), []) if c["parent_type"] == "lure_pattern")
    assert "verify here" in chunk["keywords_en"]
    assert "i-verify" in chunk["keywords_tl"]


def test_chunk_ids_are_unique():
    messages = [{"message_id": f"m{i}", "text": f"msg {i} magdeposito", "retrievable": 1,
                 "source_id": "s1"} for i in range(5)]
    chunks = build_chunks(_bundle(), messages)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_chunker.py -v
```

Expected: FAIL — `No module named 'kb.chunker'`.

- [ ] **Step 3: Implement `kb/chunker.py`**

```python
"""Flatten curated content and retrievable messages into kb_chunks rows.

Every chunk carries bilingual keyword fields. This is cross-lingual
mitigation 3 from the spec and the only one that must happen at curation
time — the runtime mitigations (multilingual embeddings, English concept
extraction before retrieval) remain open and are Allen's call.
"""

from __future__ import annotations

from kb.tagging import TAGLISH_MARKERS

MAX_CHUNK_CHARS = 2000


def split_advisory(body: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split on paragraph boundaries, hard-splitting any oversized paragraph."""
    text = (body or "").strip()
    if not text:
        return []
    chunks: list[str] = []
    buffer = ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > max_chars:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if not buffer:
            buffer = paragraph
        elif len(buffer) + 2 + len(paragraph) <= max_chars:
            buffer = f"{buffer}\n\n{paragraph}"
        else:
            chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)
    return chunks


def _tagalog_terms(text: str) -> str:
    words = [w.strip(".,!?:;()[]").lower() for w in (text or "").split()]
    found = [w for w in words if w in TAGLISH_MARKERS]
    return "; ".join(sorted(set(found)))


def _english_terms(text: str) -> str:
    words = [w.strip(".,!?:;()[]").lower() for w in (text or "").split()]
    found = [w for w in words if len(w) > 3 and w.isalpha() and w not in TAGLISH_MARKERS]
    return "; ".join(sorted(set(found))[:20])


def build_chunks(bundle: dict, messages: list[dict]) -> list[dict]:
    chunks: list[dict] = []

    def add(chunk_id, text, parent_type, parent_id, source_id, kw_en, kw_tl):
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "parent_type": parent_type,
            "parent_id": parent_id,
            "source_id": source_id,
            "keywords_en": kw_en,
            "keywords_tl": kw_tl,
        })

    for p in bundle["lure_patterns"]:
        text = (
            f"{p['name']} ({p['scam_type']}). {p['description']} "
            f"Red flags: {p['red_flags']} "
            f"Measured in {p['measured_count']} messages "
            f"({p['measured_share'] * 100:.1f}% of its slice)."
        )
        add(f"pattern:{p['pattern_id']}", text, "lure_pattern", p["pattern_id"],
            p.get("source_id") or "scottleechua-ph-sms", p["triggers_en"], p["triggers_tl"])

    for r in bundle["brand_rebuttals"]:
        text = (
            f"{r['brand_name']} official guidance: \"{r['rebuttal_quote']}\" "
            f"Official channels: {r['official_channels']}. "
            f"Official hotline: {r['official_hotline']}."
        )
        add(f"rebuttal:{r['brand_id']}", text, "brand_rebuttal", r["brand_id"],
            r["source_id"], _english_terms(text), _tagalog_terms(text))

    for a in bundle["advisories"]:
        for i, part in enumerate(split_advisory(a["body"])):
            add(f"advisory:{a['advisory_id']}:{i}", part, "advisory", a["advisory_id"],
                a["source_id"], _english_terms(part), _tagalog_terms(part))

    for m in messages:
        if not m.get("retrievable"):
            continue
        add(f"message:{m['message_id']}", m["text"], "message_example", m["message_id"],
            m["source_id"], _english_terms(m["text"]), _tagalog_terms(m["text"]))

    return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_chunker.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add knowledge-base/kb/chunker.py knowledge-base/tests/test_chunker.py
git commit -m "feat: add chunker with bilingual keyword fields"
```

---

### Task 8: Schema and database writer

**Files:**
- Create: `knowledge-base/schema/001_schema.sqlite.sql`
- Create: `knowledge-base/schema/001_schema.postgres.sql`
- Create: `knowledge-base/kb/db.py`
- Create: `knowledge-base/tests/test_db.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `EMBEDDING_DIM: int` — placeholder dimension
  - `create_schema(conn: sqlite3.Connection, schema_path: Path) -> None`
  - `insert_rows(conn, table: str, rows: list[dict]) -> int`
  - `emit_postgres_seed(conn, schema_path: Path, out_path: Path) -> Path`

- [ ] **Step 1: Write `schema/001_schema.sqlite.sql`**

```sql
-- Elderly Scam Shield knowledge base — SQLite build target.
-- The Postgres/pgvector equivalent is 001_schema.postgres.sql.
-- Embeddings are NOT populated; the provider is still undecided.

PRAGMA foreign_keys = ON;

CREATE TABLE sources (
    source_id    TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    organisation TEXT NOT NULL,
    url          TEXT NOT NULL,
    retrieved_at TEXT,
    licence      TEXT NOT NULL,
    attribution  TEXT NOT NULL,
    notes        TEXT
);

CREATE TABLE brand_rebuttals (
    brand_id           TEXT PRIMARY KEY,
    brand_name         TEXT NOT NULL,
    rebuttal_quote     TEXT NOT NULL,
    official_hotline   TEXT NOT NULL,
    official_url       TEXT NOT NULL,
    official_channels  TEXT,
    measured_frequency INTEGER NOT NULL,
    source_id          TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE lure_patterns (
    pattern_id     TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL,
    scam_type      TEXT NOT NULL,
    measured_share REAL NOT NULL,
    measured_count INTEGER NOT NULL,
    red_flags      TEXT NOT NULL,
    triggers_en    TEXT NOT NULL,
    triggers_tl    TEXT NOT NULL,
    source_id      TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE reporting_contacts (
    contact_id   TEXT PRIMARY KEY,
    organisation TEXT NOT NULL,
    hotline      TEXT,
    email        TEXT,
    url          TEXT NOT NULL,
    covers       TEXT NOT NULL,
    priority     INTEGER NOT NULL,
    source_id    TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE advisories (
    advisory_id  TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    body         TEXT NOT NULL,
    published_at TEXT,
    language     TEXT NOT NULL,
    source_id    TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE message_examples (
    message_id      TEXT PRIMARY KEY,
    text            TEXT NOT NULL,
    text_norm       TEXT NOT NULL,
    label           TEXT NOT NULL CHECK (label IN ('SCAM', 'LEGIT')),
    source_category TEXT NOT NULL,
    scam_type       TEXT,
    brand_tag       TEXT,
    has_url         INTEGER NOT NULL DEFAULT 0,
    taglish_markers INTEGER NOT NULL DEFAULT 0,
    retrievable     INTEGER NOT NULL DEFAULT 0,
    eval_holdout    INTEGER NOT NULL DEFAULT 0,
    date_received   TEXT,
    source_id       TEXT NOT NULL REFERENCES sources(source_id),
    CHECK (label <> 'LEGIT' OR retrievable = 0),
    CHECK (eval_holdout = 0 OR retrievable = 0)
);

CREATE TABLE kb_chunks (
    chunk_id    TEXT PRIMARY KEY,
    text        TEXT NOT NULL,
    parent_type TEXT NOT NULL,
    parent_id   TEXT NOT NULL,
    source_id   TEXT NOT NULL REFERENCES sources(source_id),
    keywords_en TEXT,
    keywords_tl TEXT,
    embedding   BLOB
);

CREATE INDEX idx_messages_label ON message_examples(label);
CREATE INDEX idx_messages_retrievable ON message_examples(retrievable);
CREATE INDEX idx_messages_scam_type ON message_examples(scam_type);
CREATE INDEX idx_messages_norm ON message_examples(text_norm);
CREATE INDEX idx_chunks_parent ON kb_chunks(parent_type, parent_id);
CREATE INDEX idx_chunks_source ON kb_chunks(source_id);
```

The two table-level `CHECK` constraints enforce the spec's safety rules in the database itself: a `LEGIT` row can never be retrievable, and neither can a held-out row. A future query that forgets to filter cannot reintroduce the leak.

- [ ] **Step 2: Write `schema/001_schema.postgres.sql`**

```sql
-- Elderly Scam Shield knowledge base — Supabase / PostgreSQL target.
-- Generated companion to 001_schema.sqlite.sql. Same tables, same
-- constraints, Postgres types.
--
-- vector(1536) is a PLACEHOLDER dimension. Set it to the chosen embedding
-- model's dimension, and set EMBEDDING_DIM in kb/db.py to match.
-- See HANDOFF-allen.md.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
    source_id    TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    organisation TEXT NOT NULL,
    url          TEXT NOT NULL,
    retrieved_at DATE,
    licence      TEXT NOT NULL,
    attribution  TEXT NOT NULL,
    notes        TEXT
);

CREATE TABLE brand_rebuttals (
    brand_id           TEXT PRIMARY KEY,
    brand_name         TEXT NOT NULL,
    rebuttal_quote     TEXT NOT NULL,
    official_hotline   TEXT NOT NULL,
    official_url       TEXT NOT NULL,
    official_channels  TEXT,
    measured_frequency INTEGER NOT NULL,
    source_id          TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE lure_patterns (
    pattern_id     TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL,
    scam_type      TEXT NOT NULL,
    measured_share REAL NOT NULL,
    measured_count INTEGER NOT NULL,
    red_flags      TEXT NOT NULL,
    triggers_en    TEXT NOT NULL,
    triggers_tl    TEXT NOT NULL,
    source_id      TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE reporting_contacts (
    contact_id   TEXT PRIMARY KEY,
    organisation TEXT NOT NULL,
    hotline      TEXT,
    email        TEXT,
    url          TEXT NOT NULL,
    covers       TEXT NOT NULL,
    priority     INTEGER NOT NULL,
    source_id    TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE advisories (
    advisory_id  TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    body         TEXT NOT NULL,
    published_at DATE,
    language     TEXT NOT NULL,
    source_id    TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE message_examples (
    message_id      TEXT PRIMARY KEY,
    text            TEXT NOT NULL,
    text_norm       TEXT NOT NULL,
    label           TEXT NOT NULL CHECK (label IN ('SCAM', 'LEGIT')),
    source_category TEXT NOT NULL,
    scam_type       TEXT,
    brand_tag       TEXT,
    has_url         BOOLEAN NOT NULL DEFAULT FALSE,
    taglish_markers INTEGER NOT NULL DEFAULT 0,
    retrievable     BOOLEAN NOT NULL DEFAULT FALSE,
    eval_holdout    BOOLEAN NOT NULL DEFAULT FALSE,
    date_received   TIMESTAMP,
    source_id       TEXT NOT NULL REFERENCES sources(source_id),
    CHECK (label <> 'LEGIT' OR retrievable = FALSE),
    CHECK (eval_holdout = FALSE OR retrievable = FALSE)
);

CREATE TABLE kb_chunks (
    chunk_id    TEXT PRIMARY KEY,
    text        TEXT NOT NULL,
    parent_type TEXT NOT NULL,
    parent_id   TEXT NOT NULL,
    source_id   TEXT NOT NULL REFERENCES sources(source_id),
    keywords_en TEXT,
    keywords_tl TEXT,
    embedding   vector(1536)
);

CREATE INDEX idx_messages_label ON message_examples(label);
CREATE INDEX idx_messages_retrievable ON message_examples(retrievable);
CREATE INDEX idx_messages_scam_type ON message_examples(scam_type);
CREATE INDEX idx_messages_norm ON message_examples(text_norm);
CREATE INDEX idx_chunks_parent ON kb_chunks(parent_type, parent_id);
CREATE INDEX idx_chunks_source ON kb_chunks(source_id);
```

The vector index (HNSW or IVFFlat) is deliberately absent — the right choice depends on the embedding dimension and row count, and it is Allen's call once a provider is picked.

- [ ] **Step 3: Write the failing tests**

`knowledge-base/tests/test_db.py`:

```python
import sqlite3
from pathlib import Path

import pytest

from kb.db import create_schema, emit_postgres_seed, insert_rows

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "001_schema.sqlite.sql"


@pytest.fixture()
def conn():
    connection = sqlite3.connect(":memory:")
    create_schema(connection, SCHEMA)
    connection.execute(
        "INSERT INTO sources VALUES ('s1','N','O','https://x','2026-08-06','CC BY 4.0','A','')"
    )
    return connection


def test_schema_creates_all_seven_tables(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "sources", "brand_rebuttals", "lure_patterns", "reporting_contacts",
        "advisories", "message_examples", "kb_chunks",
    } <= names


def test_insert_rows_returns_count(conn):
    rows = [{
        "pattern_id": "p1", "name": "n", "description": "d", "scam_type": "casino",
        "measured_share": 0.5, "measured_count": 5, "red_flags": "r",
        "triggers_en": "a", "triggers_tl": "b", "source_id": "s1",
    }]
    assert insert_rows(conn, "lure_patterns", rows) == 1


def test_legit_row_cannot_be_retrievable(conn):
    row = {
        "message_id": "m1", "text": "t", "text_norm": "t", "label": "LEGIT",
        "source_category": "ads", "scam_type": None, "brand_tag": None,
        "has_url": 0, "taglish_markers": 0, "retrievable": 1, "eval_holdout": 0,
        "date_received": None, "source_id": "s1",
    }
    with pytest.raises(sqlite3.IntegrityError):
        insert_rows(conn, "message_examples", [row])


def test_held_out_row_cannot_be_retrievable(conn):
    row = {
        "message_id": "m2", "text": "t", "text_norm": "t", "label": "SCAM",
        "source_category": "spam", "scam_type": "casino", "brand_tag": None,
        "has_url": 0, "taglish_markers": 0, "retrievable": 1, "eval_holdout": 1,
        "date_received": None, "source_id": "s1",
    }
    with pytest.raises(sqlite3.IntegrityError):
        insert_rows(conn, "message_examples", [row])


def test_chunk_requires_a_known_source(conn):
    row = {
        "chunk_id": "c1", "text": "t", "parent_type": "advisory", "parent_id": "a1",
        "source_id": "ghost", "keywords_en": "", "keywords_tl": "", "embedding": None,
    }
    with pytest.raises(sqlite3.IntegrityError):
        insert_rows(conn, "kb_chunks", [row])


def test_emit_postgres_seed_writes_inserts(conn, tmp_path):
    insert_rows(conn, "lure_patterns", [{
        "pattern_id": "p1", "name": "n", "description": "d'quote", "scam_type": "casino",
        "measured_share": 0.5, "measured_count": 5, "red_flags": "r",
        "triggers_en": "a", "triggers_tl": "b", "source_id": "s1",
    }])
    pg_schema = SCHEMA.parent / "001_schema.postgres.sql"
    out = emit_postgres_seed(conn, pg_schema, tmp_path / "seed.sql")
    sql = out.read_text(encoding="utf-8")
    assert "CREATE TABLE lure_patterns" in sql
    assert "INSERT INTO lure_patterns" in sql
    assert "d''quote" in sql  # single quotes escaped for Postgres
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_db.py -v
```

Expected: FAIL — `No module named 'kb.db'`.

- [ ] **Step 5: Implement `kb/db.py`**

```python
"""SQLite build target plus a Postgres seed emitter for Supabase."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Placeholder. Set when the embedding provider is chosen — see HANDOFF-allen.md.
EMBEDDING_DIM = 1536

TABLE_ORDER = (
    "sources",
    "brand_rebuttals",
    "lure_patterns",
    "reporting_contacts",
    "advisories",
    "message_examples",
    "kb_chunks",
)


def create_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    statement = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    )
    conn.executemany(statement, [tuple(r[c] for c in columns) for r in rows])
    conn.commit()
    return len(rows)


def _literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def emit_postgres_seed(
    conn: sqlite3.Connection, schema_path: Path, out_path: Path
) -> Path:
    """Write the Postgres schema followed by INSERTs for every row."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        "-- Generated by build_kb.py. Do not edit by hand.",
        "-- Apply to Supabase: psql \"$SUPABASE_DB_URL\" -f kb_seed.postgres.sql",
        "",
        schema_path.read_text(encoding="utf-8"),
        "",
    ]
    boolean_columns = {"has_url", "retrievable", "eval_holdout"}
    for table in TABLE_ORDER:
        cursor = conn.execute(f"SELECT * FROM {table}")
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        if not rows:
            parts.append(f"-- {table}: no rows\n")
            continue
        parts.append(f"-- {table}: {len(rows)} rows")
        for row in rows:
            values = []
            for column, value in zip(columns, row):
                if column in boolean_columns and value is not None:
                    values.append("TRUE" if value else "FALSE")
                elif column == "embedding":
                    values.append("NULL")
                else:
                    values.append(_literal(value))
            parts.append(
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({', '.join(values)});"
            )
        parts.append("")
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out_path
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_db.py -v
```

Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add knowledge-base/schema knowledge-base/kb/db.py knowledge-base/tests/test_db.py
git commit -m "feat: add SQLite schema, Postgres seed emitter, and retrievability constraints"
```

---

### Task 9: Build orchestration

**Files:**
- Create: `knowledge-base/scripts/build_kb.py`
- Create: `knowledge-base/out/kb.sqlite` (generated, gitignored)
- Create: `knowledge-base/out/kb_seed.postgres.sql` (generated, gitignored)
- Create: `knowledge-base/out/build_report.json` (generated, gitignored)

**Interfaces:**
- Consumes: every `kb/` module
- Produces: `out/kb.sqlite`, `out/kb_seed.postgres.sql`, `out/build_report.json` with keys `reconciliation`, `holdout`, `table_counts`, `scam_type_counts`, `brand_counts`, `fetch_summary`

- [ ] **Step 1: Implement `scripts/build_kb.py`**

```python
"""Build out/kb.sqlite and out/kb_seed.postgres.sql from content/ + the corpus.

Run from the repo root:
    knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
"""

from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from kb.chunker import build_chunks  # noqa: E402
from kb.content import (  # noqa: E402
    load_advisories,
    load_brand_rebuttals,
    load_lure_patterns,
    load_reporting_contacts,
    load_sources,
    validate_content,
)
from kb.dataset import fetch_dataset, load_rows, reconcile, usable_rows  # noqa: E402
from kb.db import TABLE_ORDER, create_schema, emit_postgres_seed, insert_rows  # noqa: E402
from kb.normalise import holdout_index, is_held_out, normalise_text  # noqa: E402
from kb.tagging import classify_scam_type, count_taglish_markers, detect_brand, has_url  # noqa: E402

import csv  # noqa: E402

CORPUS_SOURCE_ID = "scottleechua-ph-sms"
LEGIT_CATEGORIES = {"ads", "gov", "notifs"}


def load_eval_texts() -> list[str]:
    path = REPO / "eval-set-candidate-55.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        return [r["text"] for r in csv.DictReader(handle)]


def build_message_rows(rows: list[dict], eval_norms: list[str]) -> list[dict]:
    messages, seen = [], set()
    for i, row in enumerate(rows):
        norm = normalise_text(row["text"])
        if not norm or norm in seen:
            continue
        seen.add(norm)
        category = row["category"]
        label = "SCAM" if category == "spam" else "LEGIT"
        held = is_held_out(row["text"], eval_norms)
        messages.append({
            "message_id": f"msg{i:05d}",
            "text": row["text"],
            "text_norm": norm,
            "label": label,
            "source_category": category,
            "scam_type": classify_scam_type(row["text"]) if label == "SCAM" else None,
            "brand_tag": detect_brand(row["text"]),
            "has_url": int(has_url(row["text"])),
            "taglish_markers": count_taglish_markers(row["text"]),
            "retrievable": int(label == "SCAM" and not held),
            "eval_holdout": int(held),
            "date_received": row.get("date-received"),
            "source_id": CORPUS_SOURCE_ID,
        })
    return messages


def main() -> int:
    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    bundle = {
        "sources": load_sources(ROOT),
        "lure_patterns": load_lure_patterns(ROOT),
        "reporting_contacts": load_reporting_contacts(ROOT),
        "brand_rebuttals": load_brand_rebuttals(ROOT),
        "advisories": load_advisories(ROOT),
    }
    problems = validate_content(bundle)
    if problems:
        print("Content validation failed:")
        for problem in problems:
            print("  -", problem)
        return 1

    corpus_path = fetch_dataset(out_dir / "text-messages.csv")
    all_rows = load_rows(corpus_path)
    reconciliation = reconcile(all_rows)
    usable = usable_rows(all_rows)

    eval_texts = load_eval_texts()
    eval_norms = holdout_index(eval_texts)
    messages = build_message_rows(usable, eval_norms)
    matched = sum(1 for t in eval_texts if is_held_out(t, eval_norms))

    chunks = build_chunks(bundle, messages)

    db_path = out_dir / "kb.sqlite"
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(db_path)
    create_schema(conn, ROOT / "schema" / "001_schema.sqlite.sql")

    insert_rows(conn, "sources", bundle["sources"])
    insert_rows(conn, "brand_rebuttals", bundle["brand_rebuttals"])
    insert_rows(conn, "lure_patterns", bundle["lure_patterns"])
    insert_rows(conn, "reporting_contacts", bundle["reporting_contacts"])
    insert_rows(conn, "advisories", [
        {"advisory_id": a["advisory_id"], "title": a["title"], "body": a["body"],
         "published_at": a.get("published_at"), "language": a.get("language", "en"),
         "source_id": a["source_id"]}
        for a in bundle["advisories"]
    ])
    insert_rows(conn, "message_examples", messages)
    insert_rows(conn, "kb_chunks", [{**c, "embedding": None} for c in chunks])

    emit_postgres_seed(conn, ROOT / "schema" / "001_schema.postgres.sql",
                       out_dir / "kb_seed.postgres.sql")

    table_counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLE_ORDER
    }
    fetch_log_path = ROOT / "content" / "fetch_log.json"
    fetch_log = json.loads(fetch_log_path.read_text()) if fetch_log_path.exists() else {}

    report = {
        "reconciliation": reconciliation,
        "holdout": {
            "eval_rows": len(eval_texts),
            "eval_matched": matched,
            "rows_held_out": sum(m["eval_holdout"] for m in messages),
            "retrievable_messages": sum(m["retrievable"] for m in messages),
        },
        "table_counts": table_counts,
        "curated_documents": (
            table_counts["brand_rebuttals"] + table_counts["lure_patterns"]
            + table_counts["reporting_contacts"] + table_counts["advisories"]
        ),
        "scam_type_counts": dict(collections.Counter(
            m["scam_type"] for m in messages if m["label"] == "SCAM"
        )),
        "brand_counts": dict(collections.Counter(
            m["brand_tag"] for m in messages if m["label"] == "SCAM" and m["brand_tag"]
        )),
        "fetch_summary": dict(collections.Counter(
            e["status"] for e in fetch_log.values()
        )),
    }
    (out_dir / "build_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    conn.close()

    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the build**

```bash
knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
```

Expected in the printed report — these values were measured against the real data on 2026-08-06 and should reproduce exactly:

| Field | Expected |
|---|---|
| `reconciliation.ok` | `true`, all deltas `0` |
| `holdout.eval_rows` | `55` |
| `holdout.eval_matched` | `55` |
| `holdout.rows_held_out` | `53` |
| `holdout.retrievable_messages` | `692` |
| `table_counts.message_examples` | `1571` |
| `table_counts.kb_chunks` | `> 692` |
| `curated_documents` | 15–30, depending on how many advisories fetched |

**Why 53 held out and not 140.** De-duplication runs first: 1,907 usable rows collapse to 1,571 distinct normalised texts, and the 140 held-out rows collapse to 53 along with them. Both numbers are correct at their own stage. The retrievable pool is 692 rather than 1,767 because only `SCAM`-labelled rows are retrievable — the 879 hard negatives are stored but excluded by design.

If `reconciliation.ok` is `false`, or `eval_matched` is under 55, stop and report rather than proceeding.

- [ ] **Step 3: Spot-check the database by hand**

```bash
sqlite3 knowledge-base/out/kb.sqlite \
  "SELECT label, retrievable, COUNT(*) FROM message_examples GROUP BY 1,2;" \
  "SELECT parent_type, COUNT(*) FROM kb_chunks GROUP BY 1;" \
  "SELECT brand_id, official_hotline FROM brand_rebuttals;"
```

Confirm no `LEGIT` row has `retrievable = 1`.

- [ ] **Step 4: Commit**

```bash
git add knowledge-base/scripts/build_kb.py
git commit -m "feat: add build orchestration producing kb.sqlite and the Postgres seed"
```

---

### Task 10: Verification gates

**Files:**
- Create: `knowledge-base/scripts/verify_kb.py`
- Create: `knowledge-base/tests/test_verify.py`

**Interfaces:**
- Consumes: `out/kb.sqlite` from Task 9
- Produces: `run_checks(conn, eval_texts: list[str]) -> list[dict]` — each `{"name": str, "ok": bool, "detail": str}`

- [ ] **Step 1: Write the failing tests**

`knowledge-base/tests/test_verify.py`:

```python
import sqlite3
from pathlib import Path

import pytest

from kb.db import create_schema
from scripts.verify_kb import run_checks

SCHEMA = Path(__file__).resolve().parents[1] / "schema" / "001_schema.sqlite.sql"


@pytest.fixture()
def conn():
    connection = sqlite3.connect(":memory:")
    create_schema(connection, SCHEMA)
    connection.execute(
        "INSERT INTO sources VALUES ('s1','N','O','https://x','2026-08-06','CC BY 4.0','A','')"
    )
    connection.commit()
    return connection


def _add_message(conn, mid, text, retrievable=1, label="SCAM"):
    from kb.normalise import normalise_text
    conn.execute(
        "INSERT INTO message_examples VALUES (?,?,?,?,'spam',NULL,NULL,0,0,?,0,NULL,'s1')",
        (mid, text, normalise_text(text), label, retrievable),
    )
    conn.commit()


def test_clean_database_passes_every_check(conn):
    _add_message(conn, "m1", "BDO ALERT verify here")
    results = run_checks(conn, eval_texts=["Something else entirely, unrelated text"])
    assert all(r["ok"] for r in results), [r for r in results if not r["ok"]]


def test_exact_eval_leak_is_caught(conn):
    _add_message(conn, "m1", "BDO ALERT verify here at the fake domain now")
    results = {r["name"]: r for r in run_checks(
        conn, eval_texts=["BDO ALERT verify here at the fake domain now"]
    )}
    assert results["no_eval_leakage"]["ok"] is False


def test_prefix_eval_leak_is_caught(conn):
    truncated = "Get up to P2K Cashback with min. required spend at SM"
    _add_message(conn, "m1", truncated + " Appliance Center with your BDO Credit Card")
    results = {r["name"]: r for r in run_checks(conn, eval_texts=[truncated])}
    assert results["no_eval_leakage"]["ok"] is False


def test_orphaned_chunk_is_caught(conn):
    conn.execute(
        "INSERT INTO kb_chunks VALUES ('c1','t','advisory','ghost','s1','','',NULL)"
    )
    conn.commit()
    results = {r["name"]: r for r in run_checks(conn, eval_texts=[])}
    assert results["chunk_parents_resolve"]["ok"] is False


def test_source_missing_retrieved_at_is_caught(conn):
    conn.execute(
        "INSERT INTO sources VALUES ('s2','N','O','https://y','','public','A','')"
    )
    conn.commit()
    results = {r["name"]: r for r in run_checks(conn, eval_texts=[])}
    assert results["sources_have_retrieval_dates"]["ok"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_verify.py -v
```

Expected: FAIL — `No module named 'scripts.verify_kb'` (or `scripts`).

- [ ] **Step 3: Implement `scripts/verify_kb.py`**

`knowledge-base/scripts/__init__.py` already exists from Task 5, so `from scripts.verify_kb import run_checks` resolves.

```python
"""Integrity gates for the built knowledge base.

Run from the repo root:
    knowledge-base/.venv/bin/python knowledge-base/scripts/verify_kb.py

Exits non-zero if any gate fails. The build is not done until this passes.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from kb.dataset import EXPECTED_COUNTS  # noqa: E402
from kb.normalise import holdout_index, is_held_out  # noqa: E402


def _result(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def run_checks(conn: sqlite3.Connection, eval_texts: list[str]) -> list[dict]:
    results: list[dict] = []
    eval_norms = holdout_index(eval_texts)

    leaked = [
        mid for mid, text in conn.execute(
            "SELECT message_id, text FROM message_examples WHERE retrievable = 1"
        )
        if is_held_out(text, eval_norms)
    ]
    results.append(_result(
        "no_eval_leakage", not leaked,
        "clean" if not leaked else f"{len(leaked)} retrievable rows match eval text: {leaked[:5]}",
    ))

    orphans = conn.execute("""
        SELECT COUNT(*) FROM kb_chunks c WHERE NOT EXISTS (
            SELECT 1 FROM lure_patterns  p WHERE c.parent_type='lure_pattern'    AND p.pattern_id = c.parent_id
            UNION ALL
            SELECT 1 FROM brand_rebuttals b WHERE c.parent_type='brand_rebuttal' AND b.brand_id   = c.parent_id
            UNION ALL
            SELECT 1 FROM advisories     a WHERE c.parent_type='advisory'        AND a.advisory_id = c.parent_id
            UNION ALL
            SELECT 1 FROM message_examples m WHERE c.parent_type='message_example' AND m.message_id = c.parent_id
        )
    """).fetchone()[0]
    results.append(_result(
        "chunk_parents_resolve", orphans == 0, f"{orphans} orphaned chunks",
    ))

    no_source = conn.execute("""
        SELECT COUNT(*) FROM kb_chunks c
        LEFT JOIN sources s ON s.source_id = c.source_id WHERE s.source_id IS NULL
    """).fetchone()[0]
    results.append(_result(
        "chunks_have_sources", no_source == 0, f"{no_source} chunks without a source",
    ))

    undated = [
        row[0] for row in conn.execute(
            "SELECT source_id FROM sources WHERE retrieved_at IS NULL OR TRIM(retrieved_at) = ''"
        )
    ]
    results.append(_result(
        "sources_have_retrieval_dates", not undated,
        "all dated" if not undated else f"undated: {undated}",
    ))

    bad_negatives = conn.execute(
        "SELECT COUNT(*) FROM message_examples WHERE label = 'LEGIT' AND retrievable = 1"
    ).fetchone()[0]
    results.append(_result(
        "negatives_not_retrievable", bad_negatives == 0,
        f"{bad_negatives} retrievable LEGIT rows",
    ))

    blank_contacts = conn.execute("""
        SELECT COUNT(*) FROM brand_rebuttals
        WHERE TRIM(COALESCE(official_hotline,'')) = ''
           OR TRIM(COALESCE(official_url,'')) = ''
           OR TRIM(COALESCE(rebuttal_quote,'')) = ''
    """).fetchone()[0]
    results.append(_result(
        "rebuttals_complete", blank_contacts == 0,
        f"{blank_contacts} rebuttals with a blank quote, hotline, or URL",
    ))

    corpus_total = conn.execute(
        "SELECT COUNT(*) FROM message_examples"
    ).fetchone()[0]
    results.append(_result(
        "corpus_within_expected_bounds", 0 < corpus_total <= EXPECTED_COUNTS["usable"],
        f"{corpus_total} rows (usable ceiling {EXPECTED_COUNTS['usable']})",
    ))

    curated = sum(
        conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("brand_rebuttals", "lure_patterns", "reporting_contacts", "advisories")
    )
    results.append(_result(
        "curated_volume_reported", True, f"{curated} curated documents (spec estimate 25-30)",
    ))

    return results


def main() -> int:
    db_path = ROOT / "out" / "kb.sqlite"
    if not db_path.exists():
        print(f"No database at {db_path}. Run build_kb.py first.")
        return 1
    with open(REPO / "eval-set-candidate-55.csv", encoding="utf-8", newline="") as handle:
        eval_texts = [r["text"] for r in csv.DictReader(handle)]

    conn = sqlite3.connect(db_path)
    results = run_checks(conn, eval_texts)
    conn.close()

    for r in results:
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['name']:32s} {r['detail']}")
    failed = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_verify.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run the full test suite and the real verification**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests -v
knowledge-base/.venv/bin/python knowledge-base/scripts/verify_kb.py
```

Expected: all tests pass, and every gate reports PASS with exit code 0. Quote this output verbatim when reporting the task complete — do not summarise it.

- [ ] **Step 6: Commit**

```bash
git add knowledge-base/scripts/verify_kb.py knowledge-base/scripts/__init__.py knowledge-base/tests/test_verify.py
git commit -m "feat: add integrity gates for leakage, provenance, and retrievability"
```

---

### Task 11: Embedding stub, attribution, and README

**Files:**
- Create: `knowledge-base/scripts/embed.py`
- Create: `knowledge-base/kb/attribution.py`
- Create: `knowledge-base/ATTRIBUTION.md` (generated)
- Create: `knowledge-base/README.md`
- Modify: `knowledge-base/tests/test_db.py` (append the attribution test)

**Interfaces:**
- Consumes: `out/kb.sqlite`
- Produces: `render_attribution(conn) -> str`

- [ ] **Step 1: Write the failing test**

Append to `knowledge-base/tests/test_db.py`:

```python
def test_attribution_renders_every_source(conn):
    from kb.attribution import render_attribution
    conn.execute(
        "INSERT INTO sources VALUES ('s2','Second','Org','https://y','2026-08-06',"
        "'public advisory','Org public advisories.','')"
    )
    conn.commit()
    text = render_attribution(conn)
    assert "CC BY 4.0" in text
    assert "https://y" in text
    assert text.count("- **") == 2
```

- [ ] **Step 2: Run to verify it fails**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_db.py::test_attribution_renders_every_source -v
```

Expected: FAIL — `No module named 'kb.attribution'`.

- [ ] **Step 3: Implement `kb/attribution.py`**

```python
"""Render ATTRIBUTION.md from the sources table.

Generated, never hand-maintained, so the licence text and the database
cannot drift apart. The corpus is CC BY 4.0 and attribution is a licence
obligation, not a courtesy.
"""

from __future__ import annotations

import sqlite3


def render_attribution(conn: sqlite3.Connection) -> str:
    rows = conn.execute("""
        SELECT source_id, name, organisation, url, retrieved_at, licence, attribution
        FROM sources ORDER BY organisation, name
    """).fetchall()
    lines = [
        "# Attribution",
        "",
        "Generated from the `sources` table by `build_kb.py`. Do not edit by hand.",
        "",
    ]
    for sid, name, org, url, retrieved, licence, attribution in rows:
        lines += [
            f"- **{name}** — {org}",
            f"  - Source ID: `{sid}`",
            f"  - URL: {url}",
            f"  - Retrieved: {retrieved or 'not fetched'}",
            f"  - Licence: {licence}",
            f"  - Attribution: {attribution}",
            "",
        ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify it passes**

```bash
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests/test_db.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Wire attribution into the build**

In `scripts/build_kb.py`, immediately before `conn.close()`:

```python
    from kb.attribution import render_attribution
    (ROOT / "ATTRIBUTION.md").write_text(render_attribution(conn), encoding="utf-8")
```

Move that import to the top of the file with the other `kb` imports.

- [ ] **Step 6: Write `scripts/embed.py`**

```python
"""Embedding generation — NOT RUN.

The LLM provider is unresolved (open question 2 in the canonical plan) and
the Accenture Bedrock sandbox model list is unconfirmed. Populating the
embedding column requires choosing a provider, which is not this
deliverable's decision to make.

To use this script:
  1. Pick a provider and an embedding model.
  2. Set EMBEDDING_DIM in kb/db.py and vector(N) in the Postgres schema
     to that model's dimension.
  3. Implement embed_batch() below.
  4. Run: knowledge-base/.venv/bin/python knowledge-base/scripts/embed.py

Cross-lingual note: the corpus is Taglish and the advisories are English.
Mitigation 3 (bilingual keyword fields) is already applied to every chunk.
Mitigations 1 and 2 remain open — see HANDOFF-allen.md.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BATCH_SIZE = 64


def embed_batch(texts: list[str]) -> list[list[float]]:
    raise NotImplementedError(
        "No embedding provider chosen. See the module docstring and HANDOFF-allen.md."
    )


def main() -> int:
    db_path = ROOT / "out" / "kb.sqlite"
    conn = sqlite3.connect(db_path)
    pending = conn.execute(
        "SELECT COUNT(*) FROM kb_chunks WHERE embedding IS NULL"
    ).fetchone()[0]
    print(f"{pending} chunks awaiting embeddings.")
    print("No provider configured — nothing to do. This is expected.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Rebuild, verify, and write the README**

```bash
knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
knowledge-base/.venv/bin/python knowledge-base/scripts/verify_kb.py
knowledge-base/.venv/bin/python knowledge-base/scripts/embed.py
```

Write `knowledge-base/README.md` covering: what the KB is and who consumes it (RAG Agent semantically, Advisor by key); the seven tables in one line each; how to rebuild from scratch (`python -m venv`, install, `fetch_sources.py`, `build_kb.py`, `verify_kb.py`); why embeddings are absent; and the exact figures from `out/build_report.json`.

- [ ] **Step 8: Commit**

```bash
git add knowledge-base/kb/attribution.py knowledge-base/scripts knowledge-base/ATTRIBUTION.md knowledge-base/README.md knowledge-base/tests/test_db.py
git commit -m "feat: generate attribution from sources, add embed stub and README"
```

---

### Task 12: Handoff to Allen

**Files:**
- Create: `knowledge-base/HANDOFF-allen.md`

- [ ] **Step 1: Write the handoff**

Cover exactly these, using real figures from `out/build_report.json`:

1. **What exists** — table names, row counts, what each table is for.
2. **Loading into Supabase** — `psql "$SUPABASE_DB_URL" -f knowledge-base/out/kb_seed.postgres.sql`. Note that `CREATE EXTENSION vector` must succeed first, and that Supabase enables pgvector from the dashboard.
3. **The two access patterns, and why the Advisor's is not semantic.** State plainly that hotlines and rebuttal quotes are fetched by primary key, and that a fuzzy-matched hotline number given to an elderly user is a direct harm. This is the single most important paragraph in the file.
4. **Setting the embedding dimension** — `EMBEDDING_DIM` in `kb/db.py` and `vector(1536)` in `schema/001_schema.postgres.sql` must both change to match the chosen model. Then implement `embed_batch()` in `scripts/embed.py`.
5. **Decisions that remain his** — embedding model, chunk overlap (currently none), similarity threshold, top-k, and which of cross-lingual mitigations 1 and 2 to adopt on top of the keyword fields already present.
6. **Known limitations, stated plainly** — the scam-type keyword lists are a reconstruction and do not reproduce the 2026-07-29 figures exactly; near-duplicate eval leakage that is neither an exact nor a prefix match is not detected, and the corpus is heavily templated; any brand that could not be sourced has no row; any source that failed to fetch is absent, and `content/fetch_log.json` says which.
7. **Do not regenerate `ATTRIBUTION.md` by hand** — it comes from the `sources` table.

- [ ] **Step 2: Commit**

```bash
git add knowledge-base/HANDOFF-allen.md
git commit -m "docs: add Supabase handoff notes for Allen"
```

---

### Task 13: Correct stale team documents and write the slide-6 summary

**Files:**
- Create: `2026-08-06-kb-summary-for-slide6.md`
- Create: `2026-08-06-corrections-to-team-docs.md`

The canonical topic page and the deck live in the team's Obsidian vault, outside this repo. Rather than editing files that are not here, produce a corrections note that Aki, James, and Lui can apply directly.

- [ ] **Step 1: Write `2026-08-06-corrections-to-team-docs.md`**

Use this front-matter to match the folder convention:

```yaml
---
title: "Corrections to team docs — from KB build"
type: note
term: AY2526-T3
subject: STSP001-Industry-Invited-Lectures
updated: 2026-08-06
tags: [capstone, elderly-scam-shield, knowledge-base, corrections]
---
```

Each correction states the file, the exact current text, the replacement, and one line of why:

1. **`topics/capstone-elderly-scam-shield.md`, Knowledge Base section** — "Licence and label quality unverified" is false. Verified 2026-07-29 and re-verified against a fresh pull 2026-08-06: CC BY 4.0; 8,255 messages of which 1,907 have usable text; spam 827, ads 933, gov 144, notifs 3, OTP 0; coverage to 2026-06-03.
2. **Same file, same section** — the taxonomy "phishing/smishing/vishing/romance/OFW/investment/package-delivery" is disproved by the corpus. Four of seven are near-absent in SMS, vishing is inapplicable because the product accepts no audio, and the two largest real categories (gambling/casino 56.2%, bank/e-wallet impersonation 15.6%) are missing. Replace with the measured taxonomy now in `lure_patterns`.
3. **Deck slide 7, line 100** — "No public labeled Filipino/Taglish scam dataset exists (pending Nian's dataset research confirmation)" is false and disprovable in ten seconds. Replace with the dataset-research-done paragraph from `2026-07-29-nian-dataset-findings.md`.
4. **Deck slide 6** — replace with the summary in `2026-08-06-kb-summary-for-slide6.md`.
5. **Scope correction** — the June scope named BPI, BDO, GCash, Maya, Metrobank. UnionBank is #2 by measured frequency and was absent; BPI has 1 message and Metrobank 0. The KB curates GCash, UnionBank, BDO, Maya. Anywhere the old five are listed, correct them.

- [ ] **Step 2: Write `2026-08-06-kb-summary-for-slide6.md`**

Same front-matter shape. Content, using real figures from `out/build_report.json` — never rounded or remembered:

- **Headline** — the KB exists, it is a single SQL database, and it was sized from measured threat data rather than an assumed taxonomy.
- **What is in it** — the seven tables with real row counts; curated document count against the ~25–30 estimate; brand rebuttals with the brands actually sourced.
- **How it is sourced** — every entry carries a source URL, retrieval date, and licence; `ATTRIBUTION.md` is generated from the database.
- **The eval-leakage finding** — worth a line on the slide, because it is the kind of methodological care an ACN evaluator notices: the eval CSV truncates at 400 characters, five rows are prefixes of longer corpus messages, exact-match holdout would have leaked all five, and exact-or-prefix matching holds out 140 rows to protect 55.
- **What is deliberately absent** — embeddings, because the provider is unresolved. Say this as a decision, not an omission.
- **Honest gaps** — any brand not sourced; any source that failed to fetch; the scam-type keyword lists are a reconstruction and their counts differ from the 2026-07-29 figures.
- **The mentor-facing note on ruling 8** — one table per source became one row per source in a `sources` registry; provenance is intact and retrieval hits one table instead of unioning twelve.

- [ ] **Step 3: Commit**

```bash
git add 2026-08-06-kb-summary-for-slide6.md 2026-08-06-corrections-to-team-docs.md
git commit -m "docs: add slide-6 KB summary and corrections to stale team documents"
```

---

## Final verification

- [ ] **Run everything from a clean state**

```bash
rm -rf knowledge-base/out
knowledge-base/.venv/bin/python -m pytest knowledge-base/tests -v
knowledge-base/.venv/bin/python knowledge-base/scripts/build_kb.py
knowledge-base/.venv/bin/python knowledge-base/scripts/verify_kb.py
echo "verify exit: $?"
git status --short
```

Expected: every test passes, every gate reports PASS, exit code 0, and the working tree is clean apart from gitignored `out/`.

- [ ] **Report honestly.** Quote the verification output verbatim. State explicitly: which sources failed to fetch, which brands have no rebuttal row, and how far the computed scam-type counts sit from the 2026-07-29 figures. These are findings, not failures — but they must be stated, because the deck depends on them.
