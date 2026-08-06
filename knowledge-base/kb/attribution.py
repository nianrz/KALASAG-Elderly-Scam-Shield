"""Render ATTRIBUTION.md from the sources table.

Generated, never hand-maintained, so the licence text and the database
cannot drift apart. The corpus is CC BY 4.0 and attribution is a licence
obligation, not a courtesy.
"""

from __future__ import annotations

import sqlite3


def render_attribution(conn: sqlite3.Connection) -> str:
    rows = conn.execute("""
        SELECT source_id, name, organisation, url, retrieved_at, licence, attribution
        FROM sources ORDER BY organisation, name
    """).fetchall()
    lines = [
        "# Attribution",
        "",
        "Generated from the `sources` table by `build_kb.py`. Do not edit by hand.",
        "",
    ]
    for sid, name, org, url, retrieved, licence, attribution in rows:
        lines += [
            f"- **{name}** — {org}",
            f"  - Source ID: `{sid}`",
            f"  - URL: {url}",
            f"  - Retrieved: {retrieved or 'not fetched'}",
            f"  - Licence: {licence}",
            f"  - Attribution: {attribution}",
            "",
        ]
    return "\n".join(lines)
