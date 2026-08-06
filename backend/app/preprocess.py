"""Message-type detection and PII redaction. Pure functions, no LLM, no I/O.

Raw input stops here: only the redacted text and redaction labels move into
graph state. URLs are never redacted — the domain is the primary signal the
Detector needs — so URLs are shielded before the digit-run patterns fire.
"""

import re
from typing import Literal, NamedTuple

MessageType = Literal["sms", "email", "url"]

_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_EMAIL_HEADER = re.compile(r"^\s*(from|to|subject|reply-to)\s*:", re.IGNORECASE | re.MULTILINE)

# PHONE runs before ACCOUNT: a PH mobile number (09xxxxxxxxx, 11 digits) is
# also a 10-16 digit run, and the generic pattern firing first would mislabel
# every phone number as an account.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OTP", re.compile(
        r"(?i)(?:\b(?:otp|code|pin|verification)\b[^\d]{0,20}\b(\d{4,8})\b"
        r"|\b(\d{4,8})\b\D{0,20}\b(?:otp|code|pin|verification)\b)")),
    ("CARD", re.compile(r"\b\d{13,19}\b")),
    ("PHONE", re.compile(r"(?:\+639\d{9}|\b09\d{9})\b")),
    ("ACCOUNT", re.compile(r"\b\d{10,16}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]


class Preprocessed(NamedTuple):
    redacted_text: str
    message_type: MessageType
    redactions: list[str]


def detect_message_type(text: str) -> MessageType:
    stripped = text.strip()
    if _URL.fullmatch(stripped):
        return "url"
    if _EMAIL_HEADER.search(stripped):
        return "email"
    return "sms"


def redact(text: str) -> tuple[str, list[str]]:
    placeholders: dict[str, str] = {}

    def shield_url(match: re.Match[str]) -> str:
        key = f"\x00URL{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    working = _URL.sub(shield_url, text)

    labels: list[str] = []
    for label, pattern in _PATTERNS:
        def replace(match: re.Match[str], label: str = label) -> str:
            labels.append(label)
            digits = next((g for g in match.groups() if g), None)
            if digits is None:
                return f"[{label}]"
            # OTP matches span keyword + digits; only the digits are secret.
            return match.group(0).replace(digits, f"[{label}]")
        working = pattern.sub(replace, working)

    for key, url in placeholders.items():
        working = working.replace(key, url)

    seen: set[str] = set()
    unique = [l for l in labels if not (l in seen or seen.add(l))]
    return working, unique


def preprocess(text: str) -> Preprocessed:
    message_type = detect_message_type(text)
    redacted_text, redactions = redact(text)
    return Preprocessed(redacted_text, message_type, redactions)
