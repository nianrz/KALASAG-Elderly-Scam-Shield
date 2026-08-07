"""Pipeline invariant 5: eval-set messages are held out of retrieval.

This check previously existed only in knowledge-base/scripts/verify_kb.py,
which nobody runs on a backend change. msg01484 — identical to eval row
M010 but for one space before the URL — sat in the retrievable pool
undetected as a result, and the Detector could retrieve the answer to its
own test case.

Two deliberate duplications, both so this file has no import that the KB
build also has:

  * identity_key mirrors knowledge-base/kb/normalise.py. knowledge-base is
    a separate package with its own venv and is not a backend dependency.
    An independent implementation is also the stronger test: importing the
    matcher the build used would only prove the build agrees with itself.
  * KB path resolution mirrors app.config.default_kb_path, so this file
    runs without the backend venv installed. If config.py's fallback rule
    changes, change it here too.
"""

import csv
import os
import re
import sqlite3
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
FIXTURE_KB = BACKEND_ROOT / "tests" / "fixtures" / "kb_fixture.sqlite"
REAL_KB = REPO_ROOT / "knowledge-base" / "out" / "kb.sqlite"
EVAL_CSV = REPO_ROOT / "eval-set.csv"

# Alphanumeric only, Latin and Cyrillic. Scammers use Cyrillic homoglyph
# domains (9910.омск.рус), so stripping non-Latin would merge unrelated rows.
_NON_IDENTITY = re.compile(r"[^0-9a-zЀ-ӿ]+")

# Below this length a prefix match is too weak to be evidence of identity.
MIN_KEY_LEN = 20


def identity_key(text: str) -> str:
    return _NON_IDENTITY.sub("", str(text or "").lower())


def kb_path() -> Path:
    override = os.environ.get("KB_PATH")
    if override:
        return Path(override)
    return REAL_KB if REAL_KB.exists() else FIXTURE_KB


@pytest.fixture(scope="module")
def kb():
    path = kb_path()
    if not path.exists():
        pytest.skip(f"no KB at {path}")
    con = sqlite3.connect(path)
    yield con
    con.close()


@pytest.fixture(scope="module")
def eval_keys():
    if not EVAL_CSV.exists():
        pytest.skip(f"no eval set at {EVAL_CSV}")
    with open(EVAL_CSV, encoding="utf-8", newline="") as fh:
        keys = {identity_key(r["text"]) for r in csv.DictReader(fh)}
    return sorted((k for k in keys if len(k) >= MIN_KEY_LEN), key=len, reverse=True)


def test_eval_set_is_not_empty(eval_keys):
    """Guards the two fixtures above: an empty index would pass everything."""
    assert len(eval_keys) >= 80


def test_no_retrievable_message_matches_eval_text(kb, eval_keys):
    leaked = [
        mid
        for mid, text in kb.execute(
            "SELECT message_id, text FROM message_examples WHERE retrievable = 1"
        )
        if any(identity_key(text).startswith(k) for k in eval_keys)
    ]
    assert leaked == [], f"eval messages are retrievable: {leaked}"


def test_no_chunk_belongs_to_a_held_out_message(kb):
    (count,) = kb.execute(
        "SELECT COUNT(*) FROM kb_chunks c JOIN message_examples m "
        "ON c.parent_id = m.message_id WHERE m.eval_holdout = 1"
    ).fetchone()
    assert count == 0, f"{count} chunks belong to held-out messages"


def test_fragments_are_not_retrievable(kb):
    """'Hello' and 'getcash!!' are labelled SCAM upstream and are retrieval noise."""
    (count,) = kb.execute(
        "SELECT COUNT(*) FROM message_examples "
        "WHERE retrievable = 1 AND LENGTH(TRIM(text)) < 20"
    ).fetchone()
    assert count == 0, f"{count} retrievable messages under 20 characters"
