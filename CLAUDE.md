# Turtle_Server

## Purpose
Turtle Search: searchable catalog site sourced from a public Google Sheet (dive gear inventory). Password-gated (whole site), search by item name, browse by category cards, refresh button to re-pull the sheet.

## Folder layout
- `server.py` — FastAPI app (root of project, not Scripts/, since it's the deploy entrypoint uvicorn runs)
- `Scripts/scrape_sheet.py` — pulls the sheet CSV, writes `Data/items.json`
- `static/` — frontend (`index.html`, `style.css`, `app.js`)
- `Data/items.json` — current item data (category, item name, status, price), overwritten each scrape
- `deploy/` — `turtle.service` (systemd unit), `turtle_http_only.conf` (initial nginx config before SSL)
- `Handover/` — running handover doc

## Auth
Site-wide password gate, no per-user accounts, no `.env`/token needed. Password pattern: `Turtle` + `DDMMYY` (day/month/2-digit-year), computed server-side from the current date in **Asia/Jakarta (WIB, UTC+7)** — e.g. 2026-08-18 → `Turtle180826`. Both **today's and tomorrow's** password are accepted at any time (rolling grace window so the password doesn't hard-cut at midnight) — this is deliberate per user request, not a bug.
- `POST /api/login` — body `{password}` — on match, sets an httponly cookie (`turtle_auth`, 2-day max-age) whose value is a hash of the password used.
- All data/action endpoints (`/api/items`, `/api/search`, `/api/categories`, `/api/refresh`) require that cookie and re-validate it against the *current* valid-password set on every request (stateless — no server-side session store, so a restart doesn't invalidate active sessions, but a cookie naturally stops working once its password falls outside the rolling today/tomorrow window, forcing re-login roughly every 1-2 days).
- `/` and `/static/*` are NOT gated (the page shell and JS load freely) — only the data API is gated. The frontend shows a login overlay whenever `/api/items` returns 401.
- No admin token, no per-item edit feature — removed per user request 2026-08-18 once the site-wide password made the separate token redundant. Cards are display-only now.

## Data source
Google Sheet (public, link-viewable): `https://docs.google.com/spreadsheets/d/1NguyO_DeDRGLh6UgDQYRqhdwMmmP3H0V-43Bwix9sqM/edit?gid=1809562695`
Pulled via CSV export endpoint (`/export?format=csv&gid=...`), no auth needed.

Columns (row 1 header: `CODE,Bucket,Item,,Status,Discount Price`):
- A = code (used as unique key for edits)
- B = category (sheet calls it "Bucket")
- C = item name
- D = blank, ignored
- E = status
- F = discount price — parsed as plain float after stripping commas (values are US-style formatted: comma=thousands, dot=decimal, e.g. `"1,212.750"` → `1212.75`). No currency symbol assumed/displayed.

## Run locally
```
pip install -r requirements.txt
python Scripts/scrape_sheet.py         # populates Data/items.json
uvicorn server:app --host 127.0.0.1 --port 8000
```

## API
- `POST /api/login` — body `{password}` — sets session cookie on success
- `GET /api/items` — full dataset (requires session cookie)
- `GET /api/search?q=&category=` — filtered by item-name substring and/or category (requires session cookie)
- `GET /api/categories` — category list with counts (requires session cookie)
- `POST /api/refresh` — re-runs `Scripts/scrape_sheet.py` to refresh `Data/items.json` from the sheet (requires session cookie)

## Frontend behavior
- Login overlay on load if not authenticated; password field posts to `/api/login`.
- Search box filters live by item name (column C).
- Category chips filter by category (column B). Cards are display-only (category, item name, price, status) — no edit.
- Top-right Refresh button calls `/api/refresh` and re-renders with the latest sheet data.

## Deployment (Lightsail server 52.77.228.65)
- SSH: `ssh lightsail-52.77.228.65` (config alias already set in `~/.ssh/config`, key `finaldennisssh`, user `ubuntu`, sudo passwordless).
- Same pattern as sibling app `advisory` (`/var/www/advisory`, `advisory.service`, `advisory.404advisory.live`): FastAPI + `venv` + systemd unit + nginx reverse proxy + certbot.
- Deploy path: `/var/www/turtle` (git clone of `https://github.com/dnizdz/turtle_search`, pushed via SSH using the `github.com` alias in the same `~/.ssh/config`, key `finaldennisssh`).
- Port: **8002** (8001 taken by `advisory`, 5432 by postgres — confirmed via `ss -tlnp` on 2026-08-18).
- Domain: `turtle.404advisory.live` — live over HTTPS (proxied through Cloudflare; origin IPs differ from 52.77.228.65 but forward through transparently). Cert issued via certbot 2026-08-18, expires 2026-11-16, auto-renews.
- systemd unit: `deploy/turtle.service` installed at `/etc/systemd/system/turtle.service`, enabled + running.
- nginx: `/etc/nginx/sites-available/turtle` (started from `deploy/turtle_http_only.conf`, then certbot rewrote it in place to add the 443 block + HTTP→HTTPS redirect — the checked-in `deploy/turtle_http_only.conf` no longer matches what's live on the server; treat the server's copy as authoritative for the nginx config).

## Rules
- `Data/items.json` is always overwritten wholesale by `/api/refresh` (Scripts/scrape_sheet.py) — the sheet is the sole source of truth, no manual edit path exists anymore.
- Password is derived algorithmically (`Turtle` + WIB date), never stored/printed — do not hardcode a specific day's password anywhere outside this doc's example.
