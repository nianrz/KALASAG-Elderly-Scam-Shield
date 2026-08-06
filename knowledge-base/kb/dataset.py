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
from pathlib import Path

import requests

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
    """Download the corpus unless it is already cached. Never re-downloads.

    Uses requests rather than urllib.request: urllib trusts the OS trust store,
    which the python.org macOS framework build does not populate, so a clean
    rebuild there died with CERTIFICATE_VERIFY_FAILED. requests is already a
    dependency and ships its own CA bundle, so this works the same everywhere.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path
    response = requests.get(DATASET_URL, timeout=120)
    response.raise_for_status()
    cache_path.write_bytes(response.content)
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
