import importlib.util
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_eval", BACKEND_ROOT / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
sys.modules["run_eval"] = run_eval
spec.loader.exec_module(run_eval)

Record = run_eval.Record


def record(gold, first_v, first_c, second_v=None, second_c=None):
    return Record(
        message_id="M000", gold_label=gold,
        first_verdict=first_v, first_confidence=first_c,
        second_verdict=second_v, second_confidence=second_c,
        seconds=1.0,
    )


RECORDS = [
    record("SCAM", "SCAM", 0.95),
    record("SCAM", "UNCLEAR", 0.40, "LIKELY_SCAM", 0.80),
    record("SCAM", "LIKELY_LEGIT", 0.60, "LIKELY_LEGIT", 0.65),
    record("LEGIT", "LIKELY_LEGIT", 0.90),
    record("LEGIT", "LIKELY_SCAM", 0.55, "UNCLEAR", 0.50),
]


class TestVerdictAt:
    def test_below_threshold_uses_second_pass(self):
        r = record("SCAM", "UNCLEAR", 0.40, "LIKELY_SCAM", 0.80)
        assert r.verdict_at(0.70) == "LIKELY_SCAM"

    def test_at_or_above_threshold_uses_first_pass(self):
        r = record("SCAM", "UNCLEAR", 0.70, "LIKELY_SCAM", 0.80)
        assert r.verdict_at(0.70) == "UNCLEAR"

    def test_no_second_pass_falls_back_to_first(self):
        r = record("SCAM", "SCAM", 0.40)
        assert r.verdict_at(0.95) == "SCAM"


class TestMetrics:
    def test_confusion_counts_sum_to_total(self):
        counts = run_eval.confusion(RECORDS, 0.70)
        assert sum(counts.values()) == len(RECORDS)

    def test_confusion_at_070(self):
        # M1 SCAM->SCAM tp; M2 reflects->LIKELY_SCAM tp; M3 reflects->LIKELY_LEGIT fn;
        # M4 LIKELY_LEGIT tn; M5 reflects->UNCLEAR tn.
        counts = run_eval.confusion(RECORDS, 0.70)
        assert counts == {"tp": 2, "fn": 1, "tn": 2, "fp": 0}

    def test_metrics_consistent(self):
        counts = {"tp": 2, "fp": 0, "tn": 2, "fn": 1}
        m = run_eval.metrics(counts)
        assert m["accuracy"] == 0.8
        assert m["precision"] == 1.0
        assert abs(m["recall"] - 2 / 3) < 1e-9
        assert 0.0 < m["f1"] < 1.0

    def test_empty_counts_do_not_divide_by_zero(self):
        m = run_eval.metrics({"tp": 0, "fp": 0, "tn": 0, "fn": 0})
        assert m == {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}


class TestRender:
    def test_markdown_contains_all_sections_and_rows(self):
        report = run_eval.render_markdown(RECORDS, "fake:model", 0.70)
        assert "# Eval — fake:model" in report
        assert "## Confusion matrix" in report
        assert "## Threshold sweep" in report
        assert report.count("| M000 |") == len(RECORDS)
        for t in run_eval.SWEEP:
            assert f"| {t:.2f} |" in report

    def test_sweep_reflect_counts_are_monotonic(self):
        report_lines = run_eval.render_markdown(RECORDS, "fake:model", 0.70).splitlines()
        sweep_rows = [l for l in report_lines if any(l.startswith(f"| {t:.2f} |") for t in run_eval.SWEEP)]
        reflected = [int(row.split("|")[2]) for row in sweep_rows]
        assert reflected == sorted(reflected)
