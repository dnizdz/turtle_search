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
Site-wide password gate, no per-user accounts, no `.env`/token needed. Password is a **static** string, currently `qqqq`, hardcoded as `PASSWORD` in `server.py` (changed 2026-08-18 from an earlier rotating-daily-password scheme — user simplified it back to a fixed word, edit that constant + redeploy if it needs to change again).
- `POST /api/login` — body `{password}` — on match, sets an httponly cookie (`turtle_auth`, 30-day max-age).
- All data/action endpoints (`/api/items`, `/api/search`, `/api/categories`, `/api/config`, `/api/refresh`) require that cookie.
- `/` and `/static/*` are NOT gated (the page shell and JS load freely) — only the data API is gated. The frontend shows a login overlay whenever `/api/items` returns 401.
- No admin token, no per-item edit feature — cards are display-only.

## Data source
Google Sheet (public, link-viewable), URL configurable via `Data/config.json` (`{"sheet_url": "..."}`), editable from the site's top-right menu ("Spreadsheet link" field + Save — no separate auth beyond the site password). `Scripts/scrape_sheet.py` parses `sheet_id` and `gid` out of that URL with regex (`/d/<id>`, `gid=<n>`) and falls back to a hardcoded default sheet if `config.json` is missing or the URL doesn't parse. Default/original sheet: `https://docs.google.com/spreadsheets/d/1NguyO_DeDRGLh6UgDQYRqhdwMmmP3H0V-43Bwix9sqM/edit?gid=1809562695`.
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
- `GET /api/config` — current `{sheet_url}` (requires session cookie)
- `POST /api/config` — body `{sheet_url}` — validates it parses to a sheet ID, saves to `Data/config.json` (requires session cookie)
- `POST /api/refresh` — re-runs `Scripts/scrape_sheet.py` (reads `Data/config.json` for which sheet) to refresh `Data/items.json` (requires session cookie)

## Frontend behavior
- Mobile-first layout (primary usage is phone) — single-column cards below 480px, sticky header, horizontally-scrollable category chip row, large tap targets.
- Login overlay on load if not authenticated; password field posts to `/api/login`.
- Search box filters live by item name (column C).
- Category chips filter by category (column B). Cards are display-only (category, item name, price, status) — no edit.
- Header: Refresh button (calls `/api/refresh`, re-renders, shows a small bottom toast — "Refreshed" or "Refresh failed: ...") and a "⋮" menu button opening a panel with the spreadsheet-link field + Save (calls `/api/config`, also toasts on save/error).

## Deployment (Lightsail server 52.77.228.65)
- SSH: `ssh lightsail-52.77.228.65` (config alias already set in `~/.ssh/config`, key `finaldennisssh`, user `ubuntu`, sudo passwordless).
- Same pattern as sibling app `advisory` (`/var/www/advisory`, `advisory.service`, `advisory.404advisory.live`): FastAPI + `venv` + systemd unit + nginx reverse proxy + certbot.
- Deploy path: `/var/www/turtle` (git clone of `https://github.com/dnizdz/turtle_search`, pushed via SSH using the `github.com` alias in the same `~/.ssh/config`, key `finaldennisssh`).
- Port: **8002** (8001 taken by `advisory`, 5432 by postgres — confirmed via `ss -tlnp` on 2026-08-18).
- Domain: `turtle.404advisory.live` — live over HTTPS (proxied through Cloudflare; origin IPs differ from 52.77.228.65 but forward through transparently). Cert issued via certbot 2026-08-18, expires 2026-11-16, auto-renews.
- systemd unit: `deploy/turtle.service` installed at `/etc/systemd/system/turtle.service`, enabled + running.
- nginx: `/etc/nginx/sites-available/turtle` (started from `deploy/turtle_http_only.conf`, then certbot rewrote it in place to add the 443 block + HTTP→HTTPS redirect — the checked-in `deploy/turtle_http_only.conf` no longer matches what's live on the server; treat the server's copy as authoritative for the nginx config).

## Rules
- `Data/items.json` is always overwritten wholesale by `/api/refresh` (Scripts/scrape_sheet.py) — the sheet is the sole source of truth, no manual item-edit path exists.
- `Data/config.json` holds the editable sheet URL — anyone past the site password can change it via the menu; this is intentional (no separate admin gate requested), not an oversight.
