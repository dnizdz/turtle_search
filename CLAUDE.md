# Turtle_Server

## Purpose
Turtle Search: searchable catalog site sourced from a public Google Sheet (dive gear inventory). Search by item name, browse by category cards, admin menu to edit prices/status or re-pull the sheet.

## Folder layout
- `server.py` — FastAPI app (root of project, not Scripts/, since it's the deploy entrypoint uvicorn runs)
- `Scripts/scrape_sheet.py` — pulls the sheet CSV, writes `Data/items.json`
- `static/` — frontend (`index.html`, `style.css`, `app.js`)
- `Data/items.json` — current item data (category, item name, status, price), overwritten each scrape
- `deploy/` — `turtle.service` (systemd unit), `turtle_http_only.conf` (initial nginx config before SSL)
- `Handover/` — running handover doc
- `.env` / `.env.example` — `TURTLE_ADMIN_TOKEN` (admin menu auth header `X-Admin-Token`)

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
TURTLE_ADMIN_TOKEN=xxx uvicorn server:app --host 127.0.0.1 --port 8000
```

## API
- `GET /api/items` — full dataset
- `GET /api/search?q=&category=` — filtered by item-name substring and/or category
- `GET /api/categories` — category list with counts
- `POST /api/admin/update` — body `{code, item?, category?, status?, price?}`, header `X-Admin-Token` — edits one item in `Data/items.json` by code
- `POST /api/admin/reload` — header `X-Admin-Token` — re-runs `Scripts/scrape_sheet.py` to refresh `Data/items.json` from the sheet

## Frontend behavior
- Search box filters live by item name (column C).
- Category chips filter by category (column B); clicking a card opens an edit modal (admin-gated by token, not identity-gated — token typed once per session in the top-right gear menu).
- Top-right gear menu: enter admin token, trigger sheet reload.

## Deployment (Lightsail server 52.77.228.65)
- SSH: `ssh lightsail-52.77.228.65` (config alias already set in `~/.ssh/config`, key `finaldennisssh`, user `ubuntu`, sudo passwordless).
- Same pattern as sibling app `advisory` (`/var/www/advisory`, `advisory.service`, `advisory.404advisory.live`): FastAPI + `venv` + systemd unit + nginx reverse proxy + certbot.
- Deploy path: `/var/www/turtle` (git clone of `https://github.com/dnizdz/turtle_search`, pushed via SSH using the `github.com` alias in the same `~/.ssh/config`, key `finaldennisssh`).
- Port: **8002** (8001 taken by `advisory`, 5432 by postgres — confirmed via `ss -tlnp` on 2026-08-18).
- Domain: `turtle.404advisory.live` — live over HTTPS (proxied through Cloudflare; origin IPs differ from 52.77.228.65 but forward through transparently). Cert issued via certbot 2026-08-18, expires 2026-11-16, auto-renews.
- systemd unit: `deploy/turtle.service` installed at `/etc/systemd/system/turtle.service`, enabled + running.
- nginx: `/etc/nginx/sites-available/turtle` (started from `deploy/turtle_http_only.conf`, then certbot rewrote it in place to add the 443 block + HTTP→HTTPS redirect — the checked-in `deploy/turtle_http_only.conf` no longer matches what's live on the server; treat the server's copy as authoritative for the nginx config).

## Rules
- Admin token only from `.env` (`TURTLE_ADMIN_TOKEN`) — never hardcode or print in logs.
- `Data/items.json` is the live edit target for the admin "edit" flow; a "reload" overwrites it from the sheet, discarding manual edits made since the last reload — this is intentional (sheet is the source of truth on reload), not a bug.
