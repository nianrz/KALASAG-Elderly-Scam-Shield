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


# One CSV row per Record above, so the baseline has something to score.
ROWS = [
    {"gold_label": "SCAM", "has_link": "yes"},
    {"gold_label": "SCAM", "has_link": "yes"},
    {"gold_label": "SCAM", "has_link": "no"},
    {"gold_label": "LEGIT", "has_link": "no"},
    {"gold_label": "LEGIT", "has_link": "yes"},
]


class TestRender:
    def test_markdown_contains_all_sections_and_rows(self):
        report = run_eval.render_markdown(RECORDS, ROWS, "fake:model", 0.70)
        assert "# Eval — fake:model" in report
        assert "## Confusion matrix" in report
        assert "## Baseline — has_link → SCAM" in report
        assert "## Threshold sweep" in report
        assert report.count("| M000 |") == len(RECORDS)
        for t in run_eval.SWEEP:
            assert f"| {t:.2f} |" in report

    def test_sweep_reflect_counts_are_monotonic(self):
        report_lines = run_eval.render_markdown(RECORDS, ROWS, "fake:model", 0.70).splitlines()
        sweep_rows = [l for l in report_lines if any(l.startswith(f"| {t:.2f} |") for t in run_eval.SWEEP)]
        reflected = [int(row.split("|")[2]) for row in sweep_rows]
        assert reflected == sorted(reflected)

    def test_report_records_the_output_language(self):
        assert "- Output language: en" in run_eval.render_markdown(
            RECORDS, ROWS, "fake:model", 0.70, "en")


class TestBaseline:
    def test_uses_the_hand_assigned_has_link_column(self):
        rows = [
            {"gold_label": "SCAM", "has_link": "yes"},
            {"gold_label": "SCAM", "has_link": "no"},
            {"gold_label": "LEGIT", "has_link": "yes"},
            {"gold_label": "LEGIT", "has_link": "no"},
        ]
        assert run_eval.baseline_confusion(rows) == {"tp": 1, "fn": 1, "fp": 1, "tn": 1}

    def test_is_case_and_whitespace_insensitive(self):
        rows = [{"gold_label": "SCAM", "has_link": " Yes "}]
        assert run_eval.baseline_confusion(rows)["tp"] == 1

    def test_old_composition_was_near_perfect(self):
        """The defect the rebalance fixes: 32 link / 1 none / 0 / 18 was F1 0.985."""
        rows = (
            [{"gold_label": "SCAM", "has_link": "yes"}] * 32
            + [{"gold_label": "SCAM", "has_link": "no"}] * 1
            + [{"gold_label": "LEGIT", "has_link": "no"}] * 18
        )
        f1 = run_eval.metrics(run_eval.baseline_confusion(rows))["f1"]
        assert abs(f1 - 0.985) < 0.01

    def test_rebalanced_composition_is_weak(self):
        rows = (
            [{"gold_label": "SCAM", "has_link": "yes"}] * 32
            + [{"gold_label": "SCAM", "has_link": "no"}] * 13
            + [{"gold_label": "LEGIT", "has_link": "yes"}] * 20
            + [{"gold_label": "LEGIT", "has_link": "no"}] * 20
        )
        f1 = run_eval.metrics(run_eval.baseline_confusion(rows))["f1"]
        assert abs(f1 - 0.660) < 0.01


class TestResultFilename:
    def test_language_distinguishes_the_output_file(self):
        model = "bedrock_converse:global.anthropic.claude-sonnet-5"
        tl = run_eval.result_filename(model, "tl")
        en = run_eval.result_filename(model, "en")
        assert tl != en
        assert en.endswith("-en.md")
        assert ":" not in tl and "/" not in tl


class TestEvalSet:
    """Guards the composition the rebalance produced."""

    def _rows(self):
        import csv
        with open(run_eval.EVAL_CSV, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_has_eighty_five_unique_messages(self):
        rows = self._rows()
        assert len(rows) == 85
        assert len({r["text"].strip().lower() for r in rows}) == 85

    def test_every_row_is_annotated(self):
        for r in self._rows():
            assert r["has_link"] in ("yes", "no"), r["id"]
            assert r["hardness"] in ("easy", "hard"), r["id"]
            assert r["notes_for_lui"].strip(), r["id"]

    def test_link_no_longer_predicts_the_label(self):
        """The whole point. A materially higher F1 means the set drifted."""
        f1 = run_eval.metrics(run_eval.baseline_confusion(self._rows()))["f1"]
        assert abs(f1 - 0.660) < 0.05, f"baseline drifted to {f1:.3f}"
