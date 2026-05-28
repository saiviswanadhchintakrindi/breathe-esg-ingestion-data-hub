# Railway Deployment Guide — Breathe ESG Ingestion

This project deploys as **two Railway services** in one project:
- **backend** — Django REST API (Gunicorn)
- **frontend** — React/Vite (Nginx)

---

## Prerequisites

- [Railway account](https://railway.app) (free tier works)
- [Railway CLI](https://docs.railway.app/develop/cli) installed: `npm install -g @railway/cli`
- Git repo (GitHub, GitLab, or local)

---

## Step 1 — Push to GitHub

```bash
cd breathe-esg-ingestion
git init
git add .
git commit -m "initial commit"
# Create a repo on GitHub, then:
git remote add origin https://github.com/YOUR_USER/breathe-esg-ingestion.git
git push -u origin main
```

---

## Step 2 — Create Railway Project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Empty Project**
3. Name it `breathe-esg`

---

## Step 3 — Deploy Backend Service

1. In your Railway project → **+ New Service** → **GitHub Repo**
2. Select your repo
3. Set **Root Directory** → `backend`
4. Railway auto-detects the Dockerfile ✓
5. Rename the service to `backend`

### Backend Environment Variables (Settings tab)

| Variable | Value |
|---|---|
| `SECRET_KEY` | Generate one: `python -c "import secrets; print(secrets.token_hex(50))"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*.railway.app,your-custom-domain.com` |
| `CORS_ALLOW_ALL_ORIGINS` | `True` (change to `False` after setting CORS_ALLOWED_ORIGINS) |
| `PYTHONUNBUFFERED` | `1` |

Railway automatically sets `PORT` — the Dockerfile CMD uses `$PORT` already.

6. Click **Deploy** → wait for green ✓
7. Go to **Settings → Networking → Generate Domain** → copy the URL (e.g. `https://backend-production-xxxx.up.railway.app`)

---

## Step 4 — Deploy Frontend Service

1. In same Railway project → **+ New Service** → **GitHub Repo** (same repo)
2. Set **Root Directory** → `frontend`
3. Rename the service to `frontend`

### Frontend Environment Variables

| Variable | Value |
|---|---|
| `BACKEND_URL` | The backend URL from Step 3 (e.g. `https://backend-production-xxxx.up.railway.app`) |

4. Click **Deploy** → wait for green ✓
5. Go to **Settings → Networking → Generate Domain** → this is your app URL

---

## Step 5 — Update Backend CORS (after frontend deploys)

Once your frontend URL is known, update the backend env vars:

| Variable | Value |
|---|---|
| `CORS_ALLOW_ALL_ORIGINS` | `False` |
| `CORS_ALLOWED_ORIGINS` | `https://frontend-production-xxxx.up.railway.app` |

Redeploy backend after changing these.

---

## Architecture on Railway

```
Internet
   │
   ▼
[Frontend Service]  ← nginx serves React SPA on port 80
   │ /api/* proxied to →
   ▼
[Backend Service]   ← Gunicorn serves Django on $PORT
   │
   ▼
[SQLite db.sqlite3] ← persisted inside the container volume
```

> **Note on SQLite:** Railway containers are ephemeral — if the backend service
> restarts, the SQLite database resets unless you use a Railway Volume.
> For production persistence, add a Railway Volume:
> Settings → Volumes → Mount at `/app/db.sqlite3`
> Or upgrade to Railway's PostgreSQL plugin and update DATABASES in settings.py.

---

## Upgrading to PostgreSQL (recommended for production)

1. In Railway project → **+ New** → **Database** → **PostgreSQL**
2. Add to backend env vars:
   ```
   DATABASE_URL=<auto-set by Railway when you link the service>
   ```
3. Add to `requirements.txt`:
   ```
   psycopg2-binary>=2.9
   dj-database-url>=2.1
   ```
4. Update `settings.py` DATABASES:
   ```python
   import dj_database_url
   DATABASES = {
       'default': dj_database_url.config(
           default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
       )
   }
   ```

---

## Common Issues

| Issue | Fix |
|---|---|
| Backend 500 on `/api/` | Check `SECRET_KEY` is set; run `railway logs -s backend` |
| Frontend shows blank page | Check `BACKEND_URL` env var points to backend; check nginx logs |
| CORS errors in browser | Add frontend domain to `CORS_ALLOWED_ORIGINS` on backend |
| Static files 404 | `collectstatic` runs at build time in Dockerfile — check build logs |
| DB resets on redeploy | Add a Railway Volume mounted at `/app` |
