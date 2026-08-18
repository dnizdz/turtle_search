import hashlib
import json
import os
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "Data", "items.json")
SCRAPE_SCRIPT = os.path.join(ROOT, "Scripts", "scrape_sheet.py")

WIB = timezone(timedelta(hours=7))
SESSION_COOKIE = "turtle_auth"

app = FastAPI(title="Turtle Search")


def load_data():
    if not os.path.exists(DATA_PATH):
        return {"updated_at": None, "count": 0, "items": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def valid_passwords():
    now = datetime.now(WIB)
    today = now.strftime("%d%m%y")
    tomorrow = (now + timedelta(days=1)).strftime("%d%m%y")
    return {f"Turtle{today}", f"Turtle{tomorrow}"}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def valid_session_hashes():
    return {hash_password(p) for p in valid_passwords()}


def require_session(request: Request):
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie or cookie not in valid_session_hashes():
        raise HTTPException(status_code=401, detail="not authenticated")


class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginRequest):
    if body.password not in valid_passwords():
        raise HTTPException(status_code=401, detail="invalid password")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=hash_password(body.password),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 2,
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
