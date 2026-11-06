"""Inject the CSVs in ``data/`` into ``index.html`` as an inline JSON blob.

Keeps the page a single self-contained file (easy to share / host on GitHub
Pages) while the CSVs stay the single source of truth.

Usage::

    python scripts/build_data.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HTML = ROOT / "index.html"
MARKER = re.compile(r"(/\*DATA-START\*/\n).*?(\n/\*DATA-END\*/)", re.S)


def _rows(name: str) -> list[dict[str, str]]:
    with open(DATA / name, newline="") as fh:
        return list(csv.DictReader(fh))


def load_data() -> dict[str, list]:
    """Read all story CSVs into compact JSON-ready lists."""
    nasdaq = [[r["date"], float(r["close"]), r["kind"]] for r in _rows("nasdaq_closes.csv")]
    worst = [
        [r["date"], r["label"], float(r["pct"]), float(r["points"])]
        for r in _rows("worst_days.csv")
    ]
    movers = [[r["name"], float(r["pct"]), r["basis"]] for r in _rows("movers_2026-11-05.csv")]
    trail = json.loads((DATA / "trail_match.json").read_text())
    return {"nasdaq": nasdaq, "worst": worst, "movers": movers, "trail": trail}


def main() -> None:
    blob = "const DATA = " + json.dumps(load_data()) + ";"
    html = HTML.read_text()
    if not MARKER.search(html):
        raise SystemExit("DATA markers not found in index.html")
    HTML.write_text(MARKER.sub(lambda m: m.group(1) + blob + m.group(2), html))
    print(f"wrote data block to {HTML.name}")


if __name__ == "__main__":
    main()
