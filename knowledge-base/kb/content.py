"""Load and validate the hand-curated content tree."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or []


def load_sources(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "sources.yaml")


def load_lure_patterns(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "lure_patterns.yaml")


def load_reporting_contacts(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "reporting_contacts.yaml")


def load_brand_rebuttals(root: Path) -> list[dict]:
    return _load_yaml(root / "content" / "brand_rebuttals.yaml")


def load_advisories(root: Path) -> list[dict]:
    """Parse content/advisories/*.md — YAML front-matter plus verbatim body.

    Front-matter is delimited by a line that is exactly "---" (after
    stripping trailing whitespace), per the standard YAML front-matter
    convention. This deliberately does not use a naive text.split("---", 2):
    a front-matter *value* containing "---" (e.g. a scraped page title like
    "Advisory --- Phishing Alert") would otherwise land the split mid
    front-matter, silently truncating the parsed mapping instead of failing
    loudly.
    """
    directory = root / "content" / "advisories"
    if not directory.exists():
        return []
    advisories = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        if not lines or lines[0].rstrip() != "---":
            raise ValueError(f"{path} is missing YAML front-matter")
        closing_index = None
        for i in range(1, len(lines)):
            if lines[i].rstrip() == "---":
                closing_index = i
                break
        if closing_index is None:
            raise ValueError(f"{path} has unterminated front-matter")
        front = "".join(lines[1:closing_index])
        body = "".join(lines[closing_index + 1 :])
        meta = yaml.safe_load(front) or {}
        meta["body"] = body.strip()
        meta.setdefault("advisory_id", path.stem)
        advisories.append(meta)
    return advisories


def validate_content(bundle: dict) -> list[str]:
    """Return human-readable problems. Empty list means clean."""
    problems: list[str] = []
    source_ids = {s["source_id"] for s in bundle["sources"]}

    for source in bundle["sources"]:
        for field in ("url", "licence", "attribution"):
            if not str(source.get(field, "")).strip():
                problems.append(f"source {source['source_id']}: empty {field}")

    def check_ref(kind: str, key: str, rows: list[dict]) -> None:
        for row in rows:
            ref = row.get("source_id")
            if ref not in source_ids:
                problems.append(f"{kind} {row.get(key)}: unknown source_id {ref!r}")

    check_ref("contact", "contact_id", bundle["reporting_contacts"])
    check_ref("rebuttal", "brand_id", bundle["brand_rebuttals"])
    check_ref("advisory", "advisory_id", bundle["advisories"])
    check_ref("pattern", "pattern_id", bundle["lure_patterns"])

    for pattern in bundle["lure_patterns"]:
        if not str(pattern.get("triggers_tl", "")).strip():
            problems.append(f"pattern {pattern.get('pattern_id')}: empty triggers_tl")
        if not str(pattern.get("triggers_en", "")).strip():
            problems.append(f"pattern {pattern.get('pattern_id')}: empty triggers_en")

    for rebuttal in bundle["brand_rebuttals"]:
        for field in ("rebuttal_quote", "official_url"):
            if not str(rebuttal.get(field, "")).strip():
                problems.append(f"rebuttal {rebuttal.get('brand_id')}: empty {field}")

    return problems
