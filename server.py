import json
import os
import subprocess
import sys
from collections import OrderedDict

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "Data", "items.json")
SCRAPE_SCRIPT = os.path.join(ROOT, "Scripts", "scrape_sheet.py")
ADMIN_TOKEN = os.environ.get("TURTLE_ADMIN_TOKEN", "turtle-admin")

app = FastAPI(title="Turtle Search")


def load_data():
    if not os.path.exists(DATA_PATH):
        return {"updated_at": None, "count": 0, "items": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(payload):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def check_auth(x_admin_token: str | None):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


@app.get("/api/items")
def get_items():
    return load_data()


@app.get("/api/categories")
def get_categories():
    data = load_data()
    counts = OrderedDict()
    for it in data["items"]:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    return [{"category": c, "count": n} for c, n in counts.items()]


@app.get("/api/search")
def search(q: str = "", category: str = ""):
    data = load_data()
    q_lower = q.strip().lower()
    results = []
    for it in data["items"]:
        if category and it["category"] != category:
            continue
        if q_lower and q_lower not in it["item"].lower():
            continue
        results.append(it)
    return {"count": len(results), "items": results}


class ItemUpdate(BaseModel):
    code: str
    category: str | None = None
    item: str | None = None
    status: str | None = None
    price: float | None = None


@app.post("/api/admin/update")
def admin_update(update: ItemUpdate, x_admin_token: str | None = Header(default=None)):
    check_auth(x_admin_token)
    data = load_data()
    found = False
    for it in data["items"]:
        if it["code"] == update.code:
            if update.category is not None:
                it["category"] = update.category
            if update.item is not None:
                it["item"] = update.item
            if update.status is not None:
                it["status"] = update.status
            if update.price is not None:
                it["price"] = update.price
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="item code not found")
    save_data(data)
    return {"ok": True}


@app.post("/api/admin/reload")
def admin_reload(x_admin_token: str | None = Header(default=None)):
    check_auth(x_admin_token)
    result = subprocess.run(
        [sys.executable, SCRAPE_SCRIPT], capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr[-2000:])
    return {"ok": True, "log": result.stdout.strip()}


app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(ROOT, "static", "index.html"))
