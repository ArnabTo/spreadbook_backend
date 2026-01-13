# ERP Shop (Backend)

## Local setup
- Create a virtualenv and activate it:

source venv/bin/activate

- Install deps:
	- `pip install -r requirements.txt`
- Create a local env file (do not commit real secrets):
	- Copy `.env.example` to `.env` and fill values.
- Run migrations + server:

python manage.py makemigrations
python manage.py migrate
python manage.py runserver

## Demo mode (no login / no permissions)
- Set `DJANGO_DISABLE_AUTH=1` in your `.env` (or export it in the shell) to make all API endpoints accessible without authentication.
- WARNING: This is for local demo/dev only. Never enable this in production.

## Production notes (security)
- Never commit credentials or real `.env` values.
- Set `DJANGO_DEBUG=0` and provide `DJANGO_SECRET_KEY`.
- Configure `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Use HTTPS in production and keep secure cookies enabled.
- Set `DJANGO_DEFAULT_FROM_EMAIL` (default is `rakibulto@gmail.com`).

## Useful commands
- Create admin user: `python manage.py createsuperuser`
- Reset a single app migrations (dangerous; use carefully):
	- `python manage.py migrate <appname> zero`
	- `python manage.py migrate --fake <appname>`
- Kill dev ports:

	lsof -t -i tcp:8000 | xargs kill -9
lsof -t -i tcp:3075 | xargs kill -9

## CI/CD
GitHub Actions is expected to run basic checks and keep secrets in repository/environment secrets.# apibiz



1. Print End Shift Report


