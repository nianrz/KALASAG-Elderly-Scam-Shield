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
