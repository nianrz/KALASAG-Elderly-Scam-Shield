"""Eval harness: all 85 gold-labelled messages through the full pipeline.

Runs with the reflection threshold forced to 0.95 so every first pass below
0.95 also produces a second pass — that is what makes the threshold sweep
computable from one run: verdict(t) = second-pass verdict where first-pass
confidence < t, else first-pass verdict. Roughly 340 LLM calls per run;
llm.py owns the 429 backoff.

Gold labels are binary (SCAM/LEGIT); the pipeline is four-way. For metrics,
SCAM and LIKELY_SCAM count as SCAM; UNCLEAR and LIKELY_LEGIT count as
not-SCAM. Counting UNCLEAR against the scam class is the conservative
choice — an UNCLEAR on a real scam is a miss the user pays for — and the
per-message table keeps the four-way verdicts visible.

Every report carries a has_link baseline above the pipeline metrics. On the
pre-rebalance eval set that trivial rule scored F1 0.985, which no report
ever showed; a pipeline result is only meaningful against it.

Full Filipino/Taglish run (85 messages, ~340 calls):
    uv run python eval/run_eval.py

English spot-check (15 messages, ~60 calls) — catches language-directive
regressions in the en path without paying for a second full pass:
    uv run python eval/run_eval.py --language en --limit 15
"""

import argparse
import csv
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

EVAL_CSV = BACKEND_ROOT.parent / "eval-set.csv"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
SWEEP = [round(0.50 + 0.05 * i, 2) for i in range(10)]  # 0.50 … 0.95
RUN_THRESHOLD = 0.95


@dataclass
class Record:
    message_id: str
    gold_label: str
    first_verdict: str
    first_confidence: float
    second_verdict: str | None
    second_confidence: float | None
    seconds: float

    def verdict_at(self, threshold: float) -> str:
        if self.first_confidence < threshold and self.second_verdict is not None:
            return self.second_verdict
        return self.first_verdict


def is_scam(verdict: str) -> bool:
    return verdict in ("SCAM", "LIKELY_SCAM")


def confusion(records: list[Record], threshold: float) -> dict[str, int]:
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for r in records:
        predicted = is_scam(r.verdict_at(threshold))
        actual = r.gold_label == "SCAM"
        key = ("tp" if predicted else "fn") if actual else ("fp" if predicted else "tn")
        counts[key] += 1
    return counts


def baseline_confusion(rows: list[dict]) -> dict[str, int]:
    """Confusion matrix for the trivial rule: a link means SCAM.

    Reads the hand-assigned has_link column rather than detecting links.
    Detection is not reliable enough to build a control on — the corpus
    carries digit-only domains, bare IPs, Cyrillic IDNs and spaced dots,
    and the KB's own has_url column disagrees with the truth on 199 of
    1571 rows.
    """
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for row in rows:
        predicted = row["has_link"].strip().lower() == "yes"
        actual = row["gold_label"] == "SCAM"
        key = ("tp" if predicted else "fn") if actual else ("fp" if predicted else "tn")
        counts[key] += 1
    return counts


def metrics(counts: dict[str, int]) -> dict[str, float]:
    tp, fp, tn, fn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def render_markdown(
    records: list[Record], rows: list[dict], model_id: str,
    threshold: float, language: str = "tl",
) -> str:
    counts = confusion(records, threshold)
    m = metrics(counts)
    b = metrics(baseline_confusion(rows))
    lines = [
        f"# Eval — {model_id}",
        "",
        f"- Run: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Messages: {len(records)}",
        f"- Output language: {language}",
        f"- Metrics threshold: {threshold} (SCAM + LIKELY_SCAM count as SCAM; "
        "UNCLEAR counts against the scam class, the conservative mapping)",
        "",
        "## Confusion matrix",
        "",
        "| | predicted SCAM | predicted not-SCAM |",
        "|---|---|---|",
        f"| gold SCAM | {counts['tp']} | {counts['fn']} |",
        f"| gold LEGIT | {counts['fp']} | {counts['tn']} |",
        "",
        "## Baseline — has_link → SCAM",
        "",
        "Zero LLM calls. The pipeline's result below is only meaningful "
        "above this line.",
        "",
        "| accuracy | precision | recall | F1 |",
        "|---|---|---|---|",
        f"| {b['accuracy']:.3f} | {b['precision']:.3f} | {b['recall']:.3f} | {b['f1']:.3f} |",
        "",
        "## Metrics",
        "",
        "| accuracy | precision | recall | F1 |",
        "|---|---|---|---|",
        f"| {m['accuracy']:.3f} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} |",
        "",
        "## Threshold sweep",
        "",
        "verdict(t) = second-pass verdict where first-pass confidence < t.",
        "",
        "| threshold | would reflect | accuracy | precision | recall | F1 |",
        "|---|---|---|---|---|---|",
    ]
    for t in SWEEP:
        reflected = sum(1 for r in records if r.first_confidence < t)
        sm = metrics(confusion(records, t))
        lines.append(
            f"| {t:.2f} | {reflected} | {sm['accuracy']:.3f} | "
            f"{sm['precision']:.3f} | {sm['recall']:.3f} | {sm['f1']:.3f} |"
        )
    lines += [
        "",
        "## Per-message results",
        "",
        "| id | gold | 1st verdict | 1st conf | 2nd verdict | 2nd conf | seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in records:
        second_v = r.second_verdict or "—"
        second_c = f"{r.second_confidence:.2f}" if r.second_confidence is not None else "—"
        lines.append(
            f"| {r.message_id} | {r.gold_label} | {r.first_verdict} | "
            f"{r.first_confidence:.2f} | {second_v} | {second_c} | {r.seconds:.1f} |"
        )
    return "\n".join(lines) + "\n"


def result_filename(model_id: str, language: str) -> str:
    slug = model_id.replace(":", "_").replace("/", "_")
    suffix = "" if language == "tl" else f"-{language}"
    return f"{datetime.now():%Y%m%d-%H%M}-{slug}{suffix}.md"


def run(
    limit: int | None = None, out_dir: Path = RESULTS_DIR, language: str = "tl",
) -> Path:
    from app.config import get_settings
    from app.graph.build import build_graph, initial_state
    from app.llm import get_model
    from app.preprocess import preprocess
    from app.retrieval.store import ChunkStore

    model_id = get_settings().model_id
    graph = build_graph(get_model(), ChunkStore(), threshold=RUN_THRESHOLD)

    with open(EVAL_CSV, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if limit:
        rows = rows[:limit]

    records: list[Record] = []
    for i, row in enumerate(rows, 1):
        pre = preprocess(row["text"])
        started = time.time()
        state = graph.invoke(initial_state(
            pre.redacted_text, pre.message_type, pre.redactions, language,
        ))
        elapsed = time.time() - started

        reflected = state.get("reflection_count", 0) > 0
        records.append(Record(
            message_id=row["id"],
            gold_label=row["gold_label"],
            first_verdict=state["first_verdict"],
            first_confidence=state["first_confidence"],
            second_verdict=state["verdict"] if reflected else None,
            second_confidence=state["confidence"] if reflected else None,
            seconds=elapsed,
        ))
        print(f"[{i}/{len(rows)}] {row['id']} {records[-1].verdict_at(RUN_THRESHOLD)} "
              f"({elapsed:.1f}s)")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / result_filename(model_id, language)
    out_path.write_text(render_markdown(
        records, rows, model_id, get_settings().confidence_threshold, language,
    ))
    print(f"\nwrote {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="First N rows only. Use --language en --limit 15 "
                             "for the English spot-check.")
    parser.add_argument("--out", type=Path, default=RESULTS_DIR)
    parser.add_argument("--language", choices=["tl", "en"], default="tl")
    args = parser.parse_args()
    run(limit=args.limit, out_dir=args.out, language=args.language)
