"""Fetch live advisory sources to disk. Failures are recorded, never invented.

Run from the repo root:
    knowledge-base/.venv/bin/python knowledge-base/scripts/fetch_sources.py

Fetched markdown is committed, so a later build never depends on a site
still being reachable.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kb.content import load_sources  # noqa: E402

HEADERS = {"User-Agent": "STSP001-capstone-kb/1.0 (academic research; contact via GitHub)"}
TIMEOUT = 30
MIN_USEFUL_CHARS = 200

# Sources fetched as advisory documents. The corpus source is downloaded
# separately by kb.dataset, and is excluded here.
SKIP = {"scottleechua-ph-sms"}


def extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    body = "\n".join(line for line in lines if line)
    return title, body


def main() -> int:
    sources = [s for s in load_sources(ROOT) if s["source_id"] not in SKIP]
    out_dir = ROOT / "content" / "advisories"
    out_dir.mkdir(parents=True, exist_ok=True)
    log: dict[str, dict] = {}
    today = date.today().isoformat()

    for source in sources:
        sid, url = source["source_id"], source["url"]
        entry = {
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "failed",
            "http_status": None,
            "bytes": 0,
            "error": "",
        }
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            entry["http_status"] = response.status_code
            response.raise_for_status()
            title, body = extract_text(response.text)
            entry["bytes"] = len(body)
            if len(body) < MIN_USEFUL_CHARS:
                entry["status"] = "empty"
                entry["error"] = f"only {len(body)} chars of text extracted"
            else:
                front = {
                    "advisory_id": sid,
                    "title": title or source["name"],
                    "language": "en",
                    "published_at": None,
                    "source_id": sid,
                    "retrieved_at": today,
                    "retrieved_from": url,
                }
                doc = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + body + "\n"
                (out_dir / f"{sid}.md").write_text(doc, encoding="utf-8")
                entry["status"] = "ok"
        except Exception as exc:  # noqa: BLE001 - every failure mode is recorded, not raised
            entry["error"] = f"{type(exc).__name__}: {exc}"
        log[sid] = entry
        print(f"{entry['status']:>7}  {sid:32s} {entry['http_status']} {entry['bytes']}b {entry['error']}")

    (ROOT / "content" / "fetch_log.json").write_text(
        json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    ok = sum(1 for e in log.values() if e["status"] == "ok")
    print(f"\n{ok} of {len(log)} sources fetched. Failures are omitted from the KB, not invented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
