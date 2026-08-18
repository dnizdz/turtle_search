import hashlib
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "Data", "items.json")
CONFIG_PATH = os.path.join(ROOT, "Data", "config.json")
SCRAPE_SCRIPT = os.path.join(ROOT, "Scripts", "scrape_sheet.py")

PASSWORD = "qqqq"
SESSION_COOKIE = "turtle_auth"
SESSION_VALUE = hashlib.sha256(PASSWORD.encode("utf-8")).hexdigest()

app = FastAPI(title="Turtle Search")


def load_data():
    if not os.path.exists(DATA_PATH):
        return {"updated_at": None, "count": 0, "items": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"sheet_url": ""}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


SHEET_ID_RE = re.compile(r"/d/([a-zA-Z0-9-_]+)")
GID_RE = re.compile(r"[?&#]gid=(\d+)")


def parse_sheet_url(url: str):
    id_match = SHEET_ID_RE.search(url)
    if not id_match:
        return None
    gid_match = GID_RE.search(url)
    return {"sheet_id": id_match.group(1), "gid": gid_match.group(1) if gid_match else "0"}


def require_session(request: Request):
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie or cookie != SESSION_VALUE:
        raise HTTPException(status_code=401, detail="not authenticated")


class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginRequest):
    if body.password != PASSWORD:
        raise HTTPException(status_code=401, detail="invalid password")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=SESSION_VALUE,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return resp


@app.get("/api/items")
def get_items(request: Request):
    require_session(request)
    return load_data()


@app.get("/api/categories")
def get_categories(request: Request):
    require_session(request)
    data = load_data()
    counts = OrderedDict()
    for it in data["items"]:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    return [{"category": c, "count": n} for c, n in counts.items()]


@app.get("/api/search")
def search(request: Request, q: str = "", category: str = ""):
    require_session(request)
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


@app.get("/api/config")
def get_config(request: Request):
    require_session(request)
    return load_config()


class ConfigUpdate(BaseModel):
    sheet_url: str


@app.post("/api/config")
def update_config(body: ConfigUpdate, request: Request):
    require_session(request)
    parsed = parse_sheet_url(body.sheet_url)
    if not parsed:
        raise HTTPException(status_code=400, detail="could not parse a sheet ID from that URL")
    save_config({"sheet_url": body.sheet_url})
    return {"ok": True}


@app.post("/api/refresh")
def refresh(request: Request):
    require_session(request)
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
