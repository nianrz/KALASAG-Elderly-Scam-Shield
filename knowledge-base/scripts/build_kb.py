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

from kb.attribution import render_attribution  # noqa: E402
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
        # SCAM rows that matched no keyword list get scam_type None. JSON has no
        # null key, and sort_keys cannot order None against str, so name the
        # bucket instead of dropping it — its size is a real quality signal.
        "scam_type_counts": dict(collections.Counter(
            m["scam_type"] or "unclassified" for m in messages if m["label"] == "SCAM"
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
    (ROOT / "ATTRIBUTION.md").write_text(render_attribution(conn), encoding="utf-8")
    conn.close()

    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
