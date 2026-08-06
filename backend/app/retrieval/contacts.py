"""Keyed lookups for hotlines and rebuttals. No similarity search, ever.

A fuzzy-matched hotline handed to a panicking user is the one failure this
product cannot survive — contacts are fetched by primary key and passed to
the Advisor as data to reproduce verbatim.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings


@dataclass(frozen=True)
class BrandRebuttal:
    brand_id: str
    brand_name: str
    rebuttal_quote: str
    official_hotline: str
    official_url: str


@dataclass(frozen=True)
class ReportingContact:
    contact_id: str
    organisation: str
    hotline: str
    url: str


def _connect(kb_path: Path | None) -> sqlite3.Connection:
    return sqlite3.connect(Path(kb_path or get_settings().kb_path))


def known_brands(kb_path: Path | None = None) -> list[BrandRebuttal]:
    con = _connect(kb_path)
    try:
        rows = con.execute(
            "SELECT brand_id, brand_name, rebuttal_quote, official_hotline, "
            "official_url FROM brand_rebuttals"
        ).fetchall()
    finally:
        con.close()
    return [BrandRebuttal(*row) for row in rows]


def rebuttal_for_brand(brand_id: str, kb_path: Path | None = None) -> BrandRebuttal | None:
    con = _connect(kb_path)
    try:
        row = con.execute(
            "SELECT brand_id, brand_name, rebuttal_quote, official_hotline, "
            "official_url FROM brand_rebuttals WHERE brand_id = ?",
            (brand_id,),
        ).fetchone()
    finally:
        con.close()
    return BrandRebuttal(*row) if row else None


def top_contacts(n: int = 2, kb_path: Path | None = None) -> list[ReportingContact]:
    con = _connect(kb_path)
    try:
        rows = con.execute(
            "SELECT contact_id, organisation, hotline, url "
            "FROM reporting_contacts ORDER BY priority LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        con.close()
    return [ReportingContact(*row) for row in rows]
