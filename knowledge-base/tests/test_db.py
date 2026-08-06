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
