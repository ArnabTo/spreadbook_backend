# apibiz backend (Django) — DigitalOcean production setup

This folder is designed to be the root of your backend-only GitHub repository:

- Repo: https://github.com/Rakibulto/apibiz.git
- Production API domain: `apibiz.hellobiz.net`

## 1) Local development (stays local)

- Copy env:
  - `cp .env.example .env`
  - Set `DJANGO_DEBUG=1`
- Install + run:
  - `pip install -r requirements.txt`
  - `python manage.py migrate`
  - `python manage.py runserver`

## 2) GitHub repo (backend-only)

From inside this folder (recommended):

- `git init`
- `git add .`
- `git commit -m "init apibiz backend"`
- `git branch -M main`
- `git remote add origin https://github.com/Rakibulto/apibiz.git`
- `git push -u origin main`

Notes:
- Do **not** commit `.env` (already ignored).
- Keep `requirements.txt` in repo.

## 3) DigitalOcean App Platform (production)

This repo includes a reproducible app spec: `.do/app.yaml`.

### Create the app

1. DigitalOcean → **Apps** → **Create App**
2. Connect GitHub → select `Rakibulto/apibiz` → branch `main`
3. Confirm it detects a **Python** service
4. Ensure:
   - Run command matches `.do/app.yaml` (it runs `migrate`, `collectstatic`, then `gunicorn`)
   - HTTP port is `8080`

### Set production environment variables (DO UI)

Required:
- `DJANGO_SECRET_KEY` (SECRET)
- `DJANGO_ALLOWED_HOSTS=apibiz.hellobiz.net`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://apibiz.hellobiz.net`

Recommended (Postgres):
- `DATABASE_URL` (SECRET) from a DigitalOcean Managed PostgreSQL database

### Add the domain

DigitalOcean App → **Settings** → **Domains**
- Add `apibiz.hellobiz.net`
- Follow DO’s DNS instructions

## 4) About migrations

Best practice is to **commit Django migration files** to Git.
If you ignore migrations, production and development schemas will drift.
