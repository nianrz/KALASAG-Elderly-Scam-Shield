"""Flatten curated content and retrievable messages into kb_chunks rows.

Every chunk carries bilingual keyword fields. This is cross-lingual
mitigation 3 from the spec and the only one that must happen at curation
time — the runtime mitigations (multilingual embeddings, English concept
extraction before retrieval) remain open and are Allen's call.
"""

from __future__ import annotations

from kb.tagging import TAGLISH_MARKERS

MAX_CHUNK_CHARS = 2000


def split_advisory(body: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split on paragraph boundaries, hard-splitting any oversized paragraph."""
    text = (body or "").strip()
    if not text:
        return []
    chunks: list[str] = []
    buffer = ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        while len(paragraph) > max_chars:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        if not buffer:
            buffer = paragraph
        elif len(buffer) + 2 + len(paragraph) <= max_chars:
            buffer = f"{buffer}\n\n{paragraph}"
        else:
            chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)
    return chunks


def _tagalog_terms(text: str) -> str:
    words = [w.strip(".,!?:;()[]").lower() for w in (text or "").split()]
    found = [w for w in words if w in TAGLISH_MARKERS]
    return "; ".join(sorted(set(found)))


def _english_terms(text: str) -> str:
    words = [w.strip(".,!?:;()[]").lower() for w in (text or "").split()]
    found = [w for w in words if len(w) > 3 and w.isalpha() and w not in TAGLISH_MARKERS]
    return "; ".join(sorted(set(found))[:20])


def build_chunks(bundle: dict, messages: list[dict]) -> list[dict]:
    chunks: list[dict] = []

    def add(chunk_id, text, parent_type, parent_id, source_id, kw_en, kw_tl):
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "parent_type": parent_type,
            "parent_id": parent_id,
            "source_id": source_id,
            "keywords_en": kw_en,
            "keywords_tl": kw_tl,
        })

    for p in bundle["lure_patterns"]:
        text = (
            f"{p['name']} ({p['scam_type']}). {p['description']} "
            f"Red flags: {p['red_flags']} "
            f"Measured in {p['measured_count']} messages "
            f"({p['measured_share'] * 100:.1f}% of its slice)."
        )
        add(f"pattern:{p['pattern_id']}", text, "lure_pattern", p["pattern_id"],
            p.get("source_id") or "scottleechua-ph-sms", p["triggers_en"], p["triggers_tl"])

    for r in bundle["brand_rebuttals"]:
        text = (
            f"{r['brand_name']} official guidance: \"{r['rebuttal_quote']}\" "
            f"Official channels: {r['official_channels']}. "
            f"Official hotline: {r['official_hotline']}."
        )
        add(f"rebuttal:{r['brand_id']}", text, "brand_rebuttal", r["brand_id"],
            r["source_id"], _english_terms(text), _tagalog_terms(text))

    for a in bundle["advisories"]:
        for i, part in enumerate(split_advisory(a["body"])):
            add(f"advisory:{a['advisory_id']}:{i}", part, "advisory", a["advisory_id"],
                a["source_id"], _english_terms(part), _tagalog_terms(part))

    for m in messages:
        if not m.get("retrievable"):
            continue
        add(f"message:{m['message_id']}", m["text"], "message_example", m["message_id"],
            m["source_id"], _english_terms(m["text"]), _tagalog_terms(m["text"]))

    return chunks
