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

    fragments = conn.execute(
        "SELECT COUNT(*) FROM message_examples "
        "WHERE retrievable = 1 AND LENGTH(TRIM(text)) < 20"
    ).fetchone()[0]
    results.append(_result(
        "fragments_not_retrievable", fragments == 0,
        f"{fragments} retrievable messages under 20 characters",
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
    with open(REPO / "eval-set.csv", encoding="utf-8", newline="") as handle:
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
