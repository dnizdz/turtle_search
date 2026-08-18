"""Pull item data from the configured Google Sheet and write Data/items.json.

Sheet columns (row 1 header): CODE, Bucket(=Category), Item, (blank), Status, Discount Price
Sheet URL comes from Data/config.json (editable via the site's menu -> falls back
to the default sheet below if config.json is missing or unparsable).
"""
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

DEFAULT_SHEET_ID = "1NguyO_DeDRGLh6UgDQYRqhdwMmmP3H0V-43Bwix9sqM"
DEFAULT_GID = "1809562695"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "Data", "items.json")
CONFIG_PATH = os.path.join(ROOT, "Data", "config.json")

SHEET_ID_RE = re.compile(r"/d/([a-zA-Z0-9-_]+)")
GID_RE = re.compile(r"[?&#]gid=(\d+)")


def resolve_sheet_target():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        sheet_url = cfg.get("sheet_url", "")
        id_match = SHEET_ID_RE.search(sheet_url)
        if id_match:
            gid_match = GID_RE.search(sheet_url)
            return id_match.group(1), gid_match.group(1) if gid_match else "0"
    return DEFAULT_SHEET_ID, DEFAULT_GID


def parse_price(raw: str) -> int:
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        return 0
    try:
        return round(float(raw) * 1000)
    except ValueError:
        return 0


def fetch_items(csv_url):
    resp = requests.get(csv_url, timeout=30)
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
    sheet_id, gid = resolve_sheet_target()
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    items = fetch_items(csv_url)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items to {OUT_PATH} (sheet {sheet_id}, gid {gid})", flush=True)


if __name__ == "__main__":
    main()
