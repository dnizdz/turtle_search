# Handover — 2026-08-18 — Initial build

## Done
- Project scaffolded: `Scripts/`, `Data/`, `Brief/`, `static/`, `deploy/`, `Handover/`.
- `Scripts/scrape_sheet.py` — pulls public Google Sheet CSV, writes `Data/items.json`. Tested: 267 items pulled successfully.
- `server.py` — FastAPI backend: `/api/items`, `/api/search`, `/api/categories`, `/api/admin/update`, `/api/admin/reload`. Tested locally on port 8099 — all endpoints verified working, test edit reverted via re-scrape.
- `static/` frontend — search box, category chips, item cards, top-right gear menu (admin token + reload), click-card edit modal. Not yet visually checked in a browser (only API-tested).
- `deploy/turtle.service` (systemd unit, port 8002) and `deploy/turtle_http_only.conf` (nginx, HTTP-only until SSL) written, matching the existing `advisory` app's deployment pattern on the server.
- Confirmed via SSH: server reachable, sudo passwordless, ports free — chose 8002 (8001 taken by `advisory`).

## Deploy completed 2026-08-18
- Pushed to `git@github.com:dnizdz/turtle_search.git` (main branch).
- Cloned into `/var/www/turtle` on the server, venv created, deps installed.
- `.env` written on server with a freshly generated `TURTLE_ADMIN_TOKEN` (given to user in chat, not stored in repo — `.env` is gitignored, perms 600).
- `turtle.service` installed and running (systemd, port 8002, `enabled` so it survives reboot).
- `deploy/turtle_http_only.conf` installed as `/etc/nginx/sites-available/turtle`, enabled, `nginx -t` passed, reloaded.
- Verified live: `curl http://52.77.228.65/` → 200, `/api/items` → 267 items. Also verified with `Host: turtle.404advisory.live` header → 200.

## SSL completed 2026-08-18 (same session, later)
- DNS for `turtle.404advisory.live` resolved once checked again (proxied through Cloudflare — origin IPs differ from 52.77.228.65, e.g. 172.67.178.160/104.21.17.226; Cloudflare forwards to origin transparently).
- Ran `sudo certbot --nginx -d turtle.404advisory.live --non-interactive --agree-tos -m dniz.destiny@gmail.com` on the server — succeeded. Cert at `/etc/letsencrypt/live/turtle.404advisory.live/`, expires 2026-11-16, auto-renewal scheduled by certbot.
- nginx config auto-updated by certbot (443 block + HTTP→HTTPS redirect), same pattern as `advisory`/`phpplayer`.
- Verified from the server: `https://turtle.404advisory.live/` → 200, `/api/items` → 267 items, `http://turtle.404advisory.live/` → 301 redirect to HTTPS.
- Note: local dev machine's DNS resolver couldn't resolve the domain (unrelated flakiness — `Could not resolve host`), so verification was done via SSH from the server itself. If the user can't reach the site from their own machine, it's worth them flushing local DNS cache / retrying, not a server-side issue.

## Still open
- Frontend not opened in an actual browser yet — only API-level testing done (locally and on server). User should click through search/cards/admin-edit/reload once to confirm UX.
- Admin auth is a single shared token (`TURTLE_ADMIN_TOKEN`), not per-user login — acceptable per user's brief ("menu on top right corner to edit"), no identity/roles requested.

## Decisions made without explicit user sign-off (flag if wrong)
- Admin edit/reload mechanism implemented as a small FastAPI backend (not pure static HTML), since editing + saving JSON requires server-side write — static-only couldn't satisfy requirement 7.3.
- Price parsing: sheet values like `"1,212.750"` treated as US-number-format (comma=thousands, dot=decimal) → `1212.75`. No currency symbol assumed/rendered on the frontend, just the raw number formatted to 2 decimals.
- Domain picked: `turtle.404advisory.live` (matches existing `advisory.`/`phpplayer.` subdomain convention on the same server) — confirmed with user via question, not assumed silently.
- Port picked: 8002 (confirmed free on server at time of check).

## Next steps
1. `git init`, commit, add remote `git@github.com:dnizdz/turtle_search.git`, push.
2. SSH deploy: clone into `/var/www/turtle`, `python3 -m venv venv && venv/bin/pip install -r requirements.txt`, create `.env` with real `TURTLE_ADMIN_TOKEN`, run initial `Scripts/scrape_sheet.py`.
3. Install `deploy/turtle.service` → `systemctl enable --now turtle`.
4. Install `deploy/turtle_http_only.conf` → `sites-available/turtle`, symlink `sites-enabled`, `nginx -t`, reload.
5. Verify `http://52.77.228.65/` (or `Host: turtle.404advisory.live` header) serves the site.
6. Once user confirms DNS A record is live for `turtle.404advisory.live`: run `certbot --nginx -d turtle.404advisory.live` on the server.
