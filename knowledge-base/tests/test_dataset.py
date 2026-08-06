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
