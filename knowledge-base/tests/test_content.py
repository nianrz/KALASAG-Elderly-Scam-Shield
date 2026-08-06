from pathlib import Path

import pytest

from kb.content import (
    load_advisories,
    load_brand_rebuttals,
    load_lure_patterns,
    load_reporting_contacts,
    load_sources,
    validate_content,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sources_load_with_required_fields():
    sources = load_sources(ROOT)
    assert len(sources) >= 11
    ids = {s["source_id"] for s in sources}
    assert "scottleechua-ph-sms" in ids
    assert "i-arc" not in ids  # contacts are not sources
    for s in sources:
        assert s["url"].startswith("http")
        assert s["licence"]
        assert s["attribution"]


def test_lure_patterns_carry_measured_figures_and_bilingual_triggers():
    patterns = load_lure_patterns(ROOT)
    assert len(patterns) >= 10
    for p in patterns:
        assert p["triggers_en"].strip()
        assert p["triggers_tl"].strip()
        assert 0.0 < p["measured_share"] <= 1.0
        assert p["measured_count"] > 0
        # lure_patterns.source_id is NOT NULL in the schema; a missing value
        # here fails at insert time in Task 9 rather than here, so catch it now.
        assert p["source_id"] == "scottleechua-ph-sms"


def test_casino_is_the_largest_pattern():
    patterns = {p["pattern_id"]: p for p in load_lure_patterns(ROOT)}
    assert patterns["casino-promo"]["measured_count"] == 465


def test_reporting_contacts_lead_with_iarc():
    contacts = sorted(load_reporting_contacts(ROOT), key=lambda c: c["priority"])
    assert contacts[0]["contact_id"] == "i-arc-1326"
    assert contacts[0]["hotline"] == "1326"


def test_missing_optional_files_return_empty_not_error():
    assert load_brand_rebuttals(Path("/nonexistent")) == []
    assert load_advisories(Path("/nonexistent")) == []


def test_validate_flags_a_contact_pointing_at_an_unknown_source():
    bundle = {
        "sources": [{"source_id": "known", "url": "https://x", "licence": "p",
                     "attribution": "a", "retrieved_at": "2026-08-06"}],
        "lure_patterns": [],
        "reporting_contacts": [{"contact_id": "c", "source_id": "ghost", "priority": 1,
                                "organisation": "o", "hotline": "1", "email": "",
                                "url": "https://x", "covers": "c"}],
        "brand_rebuttals": [],
        "advisories": [],
    }
    problems = validate_content(bundle)
    assert any("ghost" in p for p in problems)


def test_validate_passes_on_the_real_content():
    bundle = {
        "sources": load_sources(ROOT),
        "lure_patterns": load_lure_patterns(ROOT),
        "reporting_contacts": load_reporting_contacts(ROOT),
        "brand_rebuttals": load_brand_rebuttals(ROOT),
        "advisories": load_advisories(ROOT),
    }
    assert validate_content(bundle) == []


def _write_advisory(tmp_path: Path, name: str, text: str) -> Path:
    directory = tmp_path / "content" / "advisories"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def test_front_matter_value_containing_triple_dash_parses_correctly(tmp_path):
    _write_advisory(
        tmp_path,
        "dash-in-title.md",
        "---\n"
        "title: Advisory --- Phishing Alert\n"
        "advisory_id: dash-in-title\n"
        "---\n"
        "Body text here.\n",
    )
    advisories = load_advisories(tmp_path)
    assert len(advisories) == 1
    assert advisories[0]["title"] == "Advisory --- Phishing Alert"
    assert advisories[0]["body"] == "Body text here."


def test_body_containing_triple_dash_line_parses_correctly(tmp_path):
    _write_advisory(
        tmp_path,
        "dash-in-body.md",
        "---\n"
        "title: Test\n"
        "---\n"
        "Line one\n"
        "---\n"
        "Line three\n",
    )
    advisories = load_advisories(tmp_path)
    assert len(advisories) == 1
    assert advisories[0]["title"] == "Test"
    assert advisories[0]["body"] == "Line one\n---\nLine three"


def test_unterminated_front_matter_raises(tmp_path):
    _write_advisory(
        tmp_path,
        "unterminated.md",
        "---\ntitle: Test\nno closing delimiter here\n",
    )
    with pytest.raises(ValueError, match="unterminated front-matter"):
        load_advisories(tmp_path)


def test_missing_front_matter_raises(tmp_path):
    _write_advisory(
        tmp_path,
        "no-front-matter.md",
        "Just some text\nno frontmatter here\n",
    )
    with pytest.raises(ValueError, match="missing YAML front-matter"):
        load_advisories(tmp_path)
