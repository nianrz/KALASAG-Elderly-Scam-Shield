"""Keyword tagging for corpus messages.

These keyword lists are a reconstruction. The lists behind the 2026-07-29
figures were not recorded, so derived counts will differ from those figures.
Report computed counts; do not tune these lists to reproduce old numbers.

Ordering matters: casino is checked before bank-impersonation because
casino promos routinely name GCash or Maya as a deposit channel, and a
brand mention alone is not impersonation.
"""

from __future__ import annotations

import re

_CASINO = (
    "casino", "slot", "sl0t", "jackpot", "bonus", "deposit bonus", "magdeposito",
    "mag-deposito", "cashback", "turnover", "free spin", "libreng", "manalo",
    "panalo", "raffle", "recharge", "rehistro", "magparehistro", "welcome bonus",
    "red envelope", "fishing", "bet", "taya",
)
_BANK = (
    "verify your account", "account verification", "verify here", "update your",
    "registered mobile number", "online access", "account has been", "suspended",
    "deactivat", "restricted", "on hold", "on-hold", "reactivate", "final warning",
    "sim registration", "unrecognized attempts", "data breach", "otp",
)
_JOB = ("daily salary", "part time", "part-time", "job offer", "instructor", "task", "commission")
_LOAN = ("loan", "lowrate", "low rate", "cash loan", "avail 50k", "interested call")
_PACKAGE = ("parcel", "package", "delivery", "shipment", "customs", "unpaid balance", "on hold at")
_PRIZE = ("you won", "nanalo", "winner", "prize", "claim your", "lucky", "maswerteng")
_CRYPTO = ("crypto", "bitcoin", "usdt", "investment", "trading", "forex")

_BRANDS = {
    "gcash": ("gcash", "g-cash"),
    "unionbank": ("unionbank", "union bank", "unionbnk"),
    "bdo": ("bdo", "banco de oro"),
    "maya": ("paymaya", "maya"),
    "bpi": ("bpi", "bank of the philippine islands"),
    "metrobank": ("metrobank", "metro bank"),
}

# Ordered: first match wins.
_SCAM_TYPES = (
    ("casino", _CASINO),
    ("bank-impersonation", _BANK),
    ("job-task", _JOB),
    ("package", _PACKAGE),
    ("prize", _PRIZE),
    ("loan", _LOAN),
    ("crypto", _CRYPTO),
)

TAGLISH_MARKERS = frozenset({
    "ang", "ng", "mga", "sa", "na", "ay", "para", "ka", "mo", "ko", "ito",
    "iyong", "nang", "po", "at", "kayo", "namin", "natin", "ninyo", "siya",
    "hindi", "may", "meron", "wala", "dito", "ngayon", "lang", "din", "rin",
    "kung", "dahil", "upang", "tuwing", "gamit", "makakuha", "magparehistro",
    "magdeposito", "manalo", "panalo", "libre", "libreng", "bawat", "araw",
    "iyo", "kang", "naman", "pala", "yung", "mag", "pang", "tayo", "ako",
})

_URL = re.compile(
    r"(https?://\S+|www\.\S+|\b[a-z0-9][a-z0-9\-]{1,}\.(?:com|net|org|ph|io|ai|xyz|icu|"
    r"cfd|bid|tv|uk|de|eu|mom|world|link|online|shop|site|top|vip|win|fi|mx|by|cz|show|ac|"
    r"live|store)\b\S*)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-zA-ZñÑ]+")


def _lower(text: str) -> str:
    return (text or "").lower()


def classify_scam_type(text: str) -> str | None:
    low = _lower(text)
    for label, keywords in _SCAM_TYPES:
        if any(k in low for k in keywords):
            return label
    return None


def detect_brand(text: str) -> str | None:
    low = _lower(text)
    for brand, aliases in _BRANDS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", low):
                return brand
    return None


def has_url(text: str) -> bool:
    return bool(_URL.search(text or ""))


def count_taglish_markers(text: str) -> int:
    words = {w.lower() for w in _WORD.findall(text or "")}
    return len(words & TAGLISH_MARKERS)
