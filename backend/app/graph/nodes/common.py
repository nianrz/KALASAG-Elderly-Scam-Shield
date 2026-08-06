"""Shared helpers for node functions."""

import json
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


def parse_json_reply(content):
    """Models wrap JSON in code fences or prose despite instructions.

    Bedrock Converse returns content as a list of blocks rather than a
    string; only the text blocks matter here.
    """
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    text = _FENCE.sub("", content.strip()).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
        if start == -1:
            raise
        decoder = json.JSONDecoder()
        value, _ = decoder.raw_decode(text[start:])
        return value
