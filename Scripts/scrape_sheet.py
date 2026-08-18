"""Pull item data from the public Google Sheet and write Data/items.json.

Sheet columns (row 1 header): CODE, Bucket(=Category), Item, (blank), Status, Discount Price
"""
import csv
import io
import json
import os
import sys
from datetime import datetime, timezone

import requests

SHEET_ID = "1NguyO_DeDRGLh6UgDQYRqhdwMmmP3H0V-43Bwix9sqM"
GID = "1809562695"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "Data", "items.json")


def parse_price(raw: str) -> float:
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        return 0.0
    try:
        return float(raw) * 1000
    except ValueError:
        return 0.0


def fetch_items():
    resp = requests.get(CSV_URL, timeout=30)
    resp.raise_for_status()
    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        return []
    items = []
    for row in rows[1:]:
        if len(row) < 6:
            row = row + [""] * (6 - len(row))
        code, category, item_name, _blank, status, price_raw = row[:6]
        item_name = (item_name or "").strip()
        category = (category or "").strip()
        if not item_name:
            continue
        items.append(
            {
                "code": (code or "").strip(),
                "category": category or "Uncategorized",
                "item": item_name,
                "status": (status or "").strip(),
                "price": parse_price(price_raw),
            }
        )
    return items


def main():
    items = fetch_items()
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items to {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
