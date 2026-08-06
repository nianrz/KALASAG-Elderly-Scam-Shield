from kb.chunker import MAX_CHUNK_CHARS, build_chunks, split_advisory


def test_short_advisory_is_one_chunk():
    assert split_advisory("A short advisory.") == ["A short advisory."]


def test_long_advisory_splits_on_paragraph_boundaries():
    para = "x" * 1200
    chunks = split_advisory(f"{para}\n\n{para}")
    assert len(chunks) == 2
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)


def test_oversized_paragraph_is_hard_split():
    chunks = split_advisory("y" * (MAX_CHUNK_CHARS * 2 + 50))
    assert len(chunks) == 3
    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)


def _bundle():
    return {
        "sources": [{"source_id": "s1"}],
        "lure_patterns": [{
            "pattern_id": "p1", "name": "Verify", "description": "d", "red_flags": "r",
            "scam_type": "bank-impersonation", "measured_share": 0.34, "measured_count": 44,
            "triggers_en": "verify here", "triggers_tl": "i-verify",
            "source_id": "s1",
        }],
        "reporting_contacts": [],
        "brand_rebuttals": [{
            "brand_id": "gcash", "brand_name": "GCash", "rebuttal_quote": "We never ask.",
            "official_hotline": "2882", "official_url": "https://x", "official_channels": "app",
            "measured_frequency": 39, "source_id": "s1",
        }],
        "advisories": [{"advisory_id": "a1", "title": "T", "body": "Body text.", "source_id": "s1"}],
    }


def test_build_chunks_covers_every_parent_type():
    messages = [{
        "message_id": "m1", "text": "Magdeposito ka na ngayon sa link na ito",
        "retrievable": 1, "source_id": "s1",
    }]
    chunks = build_chunks(_bundle(), messages)
    assert {c["parent_type"] for c in chunks} == {
        "lure_pattern", "brand_rebuttal", "advisory", "message_example",
    }


def test_non_retrievable_messages_are_not_chunked():
    messages = [{"message_id": "m1", "text": "held out", "retrievable": 0, "source_id": "s1"}]
    chunks = build_chunks(_bundle(), messages)
    assert not any(c["parent_type"] == "message_example" for c in chunks)


def test_every_chunk_has_source_and_bilingual_keywords():
    messages = [{"message_id": "m1", "text": "Magparehistro ka na para makakuha ng bonus",
                 "retrievable": 1, "source_id": "s1"}]
    for chunk in build_chunks(_bundle(), messages):
        assert chunk["source_id"] == "s1"
        assert chunk["keywords_en"].strip() or chunk["keywords_tl"].strip()
        assert chunk["chunk_id"]


def test_pattern_chunk_carries_both_trigger_languages():
    chunk = next(c for c in build_chunks(_bundle(), []) if c["parent_type"] == "lure_pattern")
    assert "verify here" in chunk["keywords_en"]
    assert "i-verify" in chunk["keywords_tl"]


def test_chunk_ids_are_unique():
    messages = [{"message_id": f"m{i}", "text": f"msg {i} magdeposito", "retrievable": 1,
                 "source_id": "s1"} for i in range(5)]
    chunks = build_chunks(_bundle(), messages)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
