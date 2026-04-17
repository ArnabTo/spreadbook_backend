"""
Title: Raktch ERP Shop Platform.
Description: Raktch is smart ERP solution to manage your business. you can keep track of your inventory customers, products, orders, invoices, and more.
Author: Rakibul Islam (CEO at Raktch)
Contact: rakibulto@gmail.com
www.raktch.com

"""

import os
import cloudinary
import cloudinary.api
import cloudinary.uploader
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

_env_name = (
    os.environ.get("DJANGO_ENVIRONMENT")
    or os.environ.get("DJANGO_ENV")
    or os.environ.get("ENVIRONMENT")
    or "development"
)

_env_name = _env_name.strip().lower()
ENVIRONMENT = "production" if _env_name in {
    "production", "prod"} else "development"
IS_PRODUCTION = ENVIRONMENT == "production"


def _env_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_csv(value: str | None, default: list[str] | None = None) -> list[str]:
    if value is None:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_decimal(value: str | None, default: str = "0"):
    from decimal import Decimal

    if value is None:
        return Decimal(default)
    try:
        return Decimal(value.strip())
    except Exception:
        return Decimal(default)


# take environment variables from .env (dev/local convenience)
# In production, prefer real environment variables / secret manager.
if not IS_PRODUCTION and _env_bool(os.getenv("DJANGO_LOAD_DOTENV"), default=True):
    load_dotenv()
# This is defined here as a do-nothing function because we can't import
# django.utils.translation -- that module depends on the settings.


# Cloudinary configration
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool(
    os.getenv("DJANGO_DEBUG") or os.getenv("DEBUG"),
    default=(not IS_PRODUCTION),
)

# Dev/demo mode: disable authentication/permissions entirely.
# IMPORTANT: Do not enable this in production.
DJANGO_DISABLE_AUTH = _env_bool(
    os.getenv("DJANGO_DISABLE_AUTH"), default=False)

# SECURITY WARNING: keep the secret key used in production secret!
_secret_key_env = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY")
if _secret_key_env:
    SECRET_KEY = _secret_key_env
else:
    if not IS_PRODUCTION:
        # Dev fallback only; production must provide DJANGO_SECRET_KEY.
        SECRET_KEY = "dev-insecure-secret-key-change-me"
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be set when DEBUG is False (refusing to start with an insecure default)."
        )

# ALLOWED_HOSTS = _env_csv(
#     os.getenv("DJANGO_ALLOWED_HOSTS") or os.getenv("ALLOWED_HOSTS"),
#     default=([] if IS_PRODUCTION else ["localhost", "127.0.0.1"]),
# )

if IS_PRODUCTION:
    ALLOWED_HOSTS = ["apibiz.hellobiz.net", "www.apibiz.hellobiz.net"]
    # SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # SESSION_COOKIE_SECURE = True
    # CSRF_COOKIE_SECURE = True
    # SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = None
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
else:
    ALLOWED_HOSTS = ["*", "192.168.0.101", "192.168.0.15:8000"]
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise RuntimeError(
        "DJANGO_ALLOWED_HOSTS must be set in production (comma-separated hostnames)."
    )

# Trust proxy SSL header when deployed behind a reverse proxy.
# SECURE_PROXY_SSL_HEADER = (
#     ("HTTP_X_FORWARDED_PROTO", "https")
#     if _env_bool(os.getenv("DJANGO_USE_X_FORWARDED_PROTO"), default=False)
#     else None
# )

# Cookie + HTTPS security (defaults are safe for dev; tighten for prod)
# SESSION_COOKIE_SECURE = _env_bool(
#     os.getenv("DJANGO_SESSION_COOKIE_SECURE"), default=IS_PRODUCTION
# )
# CSRF_COOKIE_SECURE = _env_bool(
#     os.getenv("DJANGO_CSRF_COOKIE_SECURE"), default=IS_PRODUCTION
# )
# SECURE_SSL_REDIRECT = _env_bool(
#     os.getenv("DJANGO_SECURE_SSL_REDIRECT"), default=IS_PRODUCTION
# )

# SECURE_HSTS_SECONDS = int(
#     os.getenv("DJANGO_SECURE_HSTS_SECONDS") or ("31536000" if IS_PRODUCTION else "0")
# )
# SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool(
#     os.getenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS"), default=IS_PRODUCTION
# )
# SECURE_HSTS_PRELOAD = _env_bool(
#     os.getenv("DJANGO_SECURE_HSTS_PRELOAD"), default=IS_PRODUCTION
# )
# SECURE_CONTENT_TYPE_NOSNIFF = _env_bool(
#     os.getenv("DJANGO_SECURE_CONTENT_TYPE_NOSNIFF"), default=True
# )
# SECURE_REFERRER_POLICY = os.getenv("DJANGO_SECURE_REFERRER_POLICY") or "same-origin"
# X_FRAME_OPTIONS = os.getenv("DJANGO_X_FRAME_OPTIONS") or "DENY"

# POS configuration
# Maximum allowed cash short waiver for cash payments (in currency units, e.g., BDT).
# Example: POS_CASH_WAIVER_MAX=10
POS_CASH_WAIVER_MAX = _env_decimal(
    os.getenv("POS_CASH_WAIVER_MAX"), default="10")

# Additional security headers/policies
SECURE_CROSS_ORIGIN_OPENER_POLICY = (
    os.getenv("DJANGO_SECURE_CROSS_ORIGIN_OPENER_POLICY") or "same-origin"
)
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = (
    os.getenv("DJANGO_SECURE_CROSS_ORIGIN_RESOURCE_POLICY") or "same-site"
)

# Cookie SameSite (override in env if you run cross-site cookies)
SESSION_COOKIE_SAMESITE = os.getenv("DJANGO_SESSION_COOKIE_SAMESITE") or "Lax"
CSRF_COOKIE_SAMESITE = os.getenv("DJANGO_CSRF_COOKIE_SAMESITE") or "Lax"

# CORS/CSRF
# In production: set DJANGO_CORS_ALLOWED_ORIGINS and DJANGO_CSRF_TRUSTED_ORIGINS.
CORS_ALLOW_CREDENTIALS = _env_bool(
    os.getenv("DJANGO_CORS_ALLOW_CREDENTIALS"), default=True
)

# NOTE: django-cors-headers uses CORS_ALLOW_ALL_ORIGINS (CORS_ORIGIN_ALLOW_ALL is legacy).
# For local dev we default to allowing all origins when DEBUG is true, to avoid
# the "only OPTIONS requests" symptom when the frontend origin doesn't exactly match.
CORS_ALLOW_ALL_ORIGINS = _env_bool(
    os.getenv("DJANGO_CORS_ALLOW_ALL"),
    default=(not IS_PRODUCTION),
)
CORS_ORIGIN_ALLOW_ALL = CORS_ALLOW_ALL_ORIGINS

_default_cors = (
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if not IS_PRODUCTION
    else []
)
CORS_ALLOWED_ORIGINS = _env_csv(
    os.getenv("DJANGO_CORS_ALLOWED_ORIGINS"), default=_default_cors
)
CSRF_TRUSTED_ORIGINS = _env_csv(
    os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS"), default=[])

# Convenience: In production, if CSRF trusted origins aren't explicitly provided,
# default them from the CORS allowed origins.
# Django expects scheme+host (e.g. https://example.com).
if IS_PRODUCTION and not CSRF_TRUSTED_ORIGINS and not CORS_ALLOW_ALL_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        origin
        for origin in CORS_ALLOWED_ORIGINS
        if origin.startswith("https://") or origin.startswith("http://")
    ]
SITE_ID = 1

# Application definition

DJANGO_COMMON_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sessions",
]

THIRD_PARTY_APPS = [
    "django_crontab",
    "import_export",
    "django_user_agents",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "django_filters",
    "crispy_forms",
    "django_countries",
    "phonenumber_field",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "defender",
    "zxcvbn_password",
    "taggit",
    "schedule",
    "ckeditor",
    "ckeditor_uploader",
    # 'cloudinary_storage',
    # 'cloudinary',
    "rest_framework",
    "rest_framework.authtoken",
    "djoser",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # Backup
    "dbbackup",
]

# # Backup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {"location": BASE_DIR / "backup"}

CRONJOBS = [
    ("*/1 * * * *", "ERP_Shop.cron.my_backup"),
    ("0 2 * * *", "ERP_Shop.cron.subscription_maintenance"),
]


LOCAL_APPS = [
    "accounts.apps.AccountsConfig",
    "analytics.apps.AnalyticsConfig",
    "authenticator.apps.AuthenticatorConfig",
    "banking.apps.BankingConfig",
    "blog.apps.BlogConfig",
    "booking.apps.BookingConfig",
    "bouche.apps.BoucheConfig",
    "calendar_event.apps.CalendarEventConfig",
    "calendar_events.apps.CalendarEventsConfig",
    "chat.apps.ChatConfig",
    "hotel.apps.HotelConfig",
    "resort.apps.ResortConfig",
    "common.apps.CommonConfig",
    "company.apps.CompanyConfig",
    "contact.apps.ContactConfig",
    "core.apps.CoreConfig",
    "customers.apps.CustomersConfig",
    "damage.apps.DamageConfig",
    "e_commerc.apps.ECommercConfig",
    "expense.apps.ExpenseConfig",
    "income.apps.IncomeConfig",
    "hr.apps.HrConfig",
    "invoice.apps.InvoiceConfig",
    "job.apps.JobConfig",
    "mail.apps.MailConfig",
    "my_project.apps.MyProjectConfig",
    "notification.apps.NotificationConfig",
    "order.apps.OrderConfig",
    "payment.apps.PaymentConfig",
    "portfolio.apps.PortfolioConfig",
    "products.apps.ProductsConfig",
    "profiles.apps.ProfilesConfig",
    "promotions_discounts.apps.PromotionsDiscountsConfig",
    "pharmacy.apps.PharmacyConfig",
    "inventory_log.apps.InventoryLogConfig",
    "purchase.apps.PurchaseConfig",
    "payroll.apps.PayrollConfig",
    "reseller.apps.ResellerConfig",
    "returns.apps.ReturnsConfig",
    "review.apps.ReviewConfig",
    "sales.apps.SalesConfig",
    "service.apps.ServiceConfig",
    "settings.apps.SettingsConfig",
    "staff.apps.StaffConfig",
    "stock.apps.StockConfig",
    "suppliers.apps.SuppliersConfig",
    "menu_items.apps.MenuItemsConfig",
    "recipe_waste_management.apps.RecipeWasteManagementConfig",
    "dashboard.apps.DashboardConfig",
    "reports.apps.ReportsConfig",
    "table_managment.apps.TableManagmentConfig",
    "tour.apps.TourConfig",
    "website_page_hanlde.apps.WebsitePageHanldeConfig",
    "supplier_ledger.apps.SupplierLedgerConfig",
]

INSTALLED_APPS = DJANGO_COMMON_APPS + LOCAL_APPS + THIRD_PARTY_APPS

# Import-Export settings for large file handling
IMPORT_EXPORT_TMP_STORAGE_CLASS = "import_export.tmp_storages.CacheStorage"


# If auth is disabled, patch common DRF auth/permission classes so that viewsets
# that hardcode TokenAuthentication/IsAuthenticated won't block requests.
if DJANGO_DISABLE_AUTH:
    try:
        import rest_framework.authentication
        import rest_framework.permissions

        from ERP_Shop.demo_auth import TokenAuthenticationWithDemo

        rest_framework.authentication.TokenAuthentication = TokenAuthenticationWithDemo

        from rest_framework.permissions import IsAuthenticated as _IsAuthenticated

        class _IsAuthenticatedAllowAll(_IsAuthenticated):
            def has_permission(self, request, view):
                return True

        rest_framework.permissions.IsAuthenticated = _IsAuthenticatedAllowAll
    except Exception:
        # Avoid blocking startup if DRF isn't importable for some reason.
        pass


# Thousand separator symbol
THOUSAND_SEPARATOR = ","
PHONENUMBER_DEFAULT_REGION = "BD"
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CKEDITOR_BASEPATH = "/static/ckeditor/ckeditor/"
CKEDITOR_UPLOAD_PATH = "uploads/"

##############
# MIDDLEWARE #
##############

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    # Third party middleware📌
    "defender.middleware.FailedLoginMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django_user_agents.middleware.UserAgentMiddleware",
    # Custom middleware📌
    # 'core.middleware.activity.UserActivityMiddleware',
    # 'core.middleware.visitors.UserStatisticsMiddleware',
    # 'core.middleware.requests.RequestMiddleware',
]

ROOT_URLCONF = "ERP_Shop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "ERP_Shop.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

_database_url = os.getenv("DATABASE_URL") or os.getenv("DJANGO_DATABASE_URL")
if _database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=int(os.getenv("DJANGO_DB_CONN_MAX_AGE") or 60),
            ssl_require=_env_bool(
                os.getenv("DJANGO_DB_SSL_REQUIRE"), default=not DEBUG
            ),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 20,
            },
        }
    }

##################
# AUTHENTICATION #
##################

AUTH_USER_MODEL = "authenticator.User"

# LOGIN_REDIRECT_URL = '/dashboard'

# LOGIN_URL = '/auth/sign-in/'

# LOGOUT_REDIRECT_URL = '/'


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "zxcvbn_password.ZXCVBNValidator",
        "OPTIONS": {
            "min_score": 3,
            "user_attributes": ("email", "organization_name", "owner_name"),
        },
    },
]

EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND") or (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST") or "smtp.gmail.com"
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT") or 587)
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER") or ""
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD") or ""
EMAIL_USE_TLS = _env_bool(os.getenv("DJANGO_EMAIL_USE_TLS"), default=True)
DEFAULT_FROM_EMAIL = (
    os.getenv(
        "DJANGO_DEFAULT_FROM_EMAIL") or EMAIL_HOST_USER or "rakibulto@gmail.com"
)

# Used for error emails (if you enable them) and server-side notifications.
SERVER_EMAIL = os.getenv("DJANGO_SERVER_EMAIL") or DEFAULT_FROM_EMAIL


# The list of routers that will be used to determine which database to use when performing a database query.
# DATABASE_ROUTERS = ['database.routers.db_routers.ExpenseRouter']

# Caching (optional)
# - Dev default: in-memory cache (no extra services needed)
# - Production: set DJANGO_REDIS_URL to enable Redis-backed caching
DJANGO_REDIS_URL = os.getenv("DJANGO_REDIS_URL")
DJANGO_CACHE_KEY_PREFIX = os.getenv("DJANGO_CACHE_KEY_PREFIX") or "rms"
DJANGO_CACHE_TIMEOUT = int(os.getenv("DJANGO_CACHE_TIMEOUT") or 300)

# django-defender requires a Redis URL; fall back to a local Redis default so
# the middleware module can be imported even when DEFENDER_REDIS_URL is not set.
# Set DEFENDER_REDIS_URL env-var to override in production.
DEFENDER_REDIS_URL = os.getenv("DEFENDER_REDIS_URL") or os.getenv(
    "DJANGO_REDIS_URL") or "redis://127.0.0.1:6379/0"

if DJANGO_REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": DJANGO_REDIS_URL,
            "TIMEOUT": DJANGO_CACHE_TIMEOUT,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": int(
                        os.getenv("DJANGO_REDIS_MAX_CONNECTIONS") or 100
                    ),
                    "retry_on_timeout": True,
                },
                "SOCKET_CONNECT_TIMEOUT": int(
                    os.getenv("DJANGO_REDIS_SOCKET_CONNECT_TIMEOUT") or 5
                ),
                "SOCKET_TIMEOUT": int(os.getenv("DJANGO_REDIS_SOCKET_TIMEOUT") or 5),
            },
            "KEY_PREFIX": DJANGO_CACHE_KEY_PREFIX,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "rms-locmem",
            "TIMEOUT": DJANGO_CACHE_TIMEOUT,
        }
    }

# Optional: cache-backed sessions (recommended when using Redis)
if _env_bool(os.getenv("DJANGO_SESSION_CACHE"), default=False):
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Dhaka"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
CRISPY_TEMPLATE_PACK = "bootstrap4"
# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Allow bulk admin actions (e.g. deleting thousands of records at once).
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100_000

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": (
        ["rest_framework.permissions.AllowAny"]
        if DJANGO_DISABLE_AUTH
        else (
            [
                "common.permissions.SubscriptionActivePermission",
                "rest_framework.permissions.IsAuthenticated",
            ]
            if _env_bool(os.getenv("DJANGO_ENFORCE_SUBSCRIPTION"), default=False)
            else ["rest_framework.permissions.IsAuthenticated"]
        )
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        ("ERP_Shop.demo_auth.DemoAuthentication",)
        if DJANGO_DISABLE_AUTH
        else (
            "rest_framework.authentication.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework_simplejwt.authentication.JWTAuthentication",
        )
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,  # Default page size for pagination
}

# OWASP-style API rate limiting (optional)
if _env_bool(os.getenv("DJANGO_ENABLE_THROTTLING"), default=False):
    REST_FRAMEWORK.update(
        {
            "DEFAULT_THROTTLE_CLASSES": (
                "rest_framework.throttling.AnonRateThrottle",
                "rest_framework.throttling.UserRateThrottle",
            ),
            "DEFAULT_THROTTLE_RATES": {
                "anon": os.getenv("DJANGO_THROTTLE_ANON") or "100/min",
                "user": os.getenv("DJANGO_THROTTLE_USER") or "1000/min",
            },
        }
    )

AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

SIMPLE_JWT = {
    # 'AUTH_HEADER_TYPES': ('JWT',),
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=15),
    # 'AUTH_TOKEN_CLASSES': (
    #     'rest_framework_simplejwt.tokens.AccessToken',
    # )
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL") or ("DEBUG" if DEBUG else "INFO"),
    },
}


DJOSER = {
    "DOMAIN": os.getenv("DJOSER_DOMAIN")
    or os.getenv("DJANGO_DOMAIN")
    or "localhost:8000",
    "LOGIN_FIELD": "email",
    "USER_ID_FIELD": "name",
    "USER_CREATE_PASSWORD_RETYPE": True,
    "USERNAME_CHANGED_EMAIL_CONFIRMATION": True,
    "PASSWORD_CHANGED_EMAIL_CONFIRMATION": True,
    "SEND_CONFIRMATION_EMAIL": True,
    "SET_USERNAME_RETYPE": True,
    "SET_PASSWORD_RETYPE": True,
    "PASSWORD_RESET_CONFIRM_URL": "password/reset/confirm/{uid}/{token}",
    "USERNAME_RESET_CONFIRM_URL": "email/reset/confirm/{uid}/{token}",
    "ACTIVATION_URL": "activate/{uid}/{token}",
    "SEND_ACTIVATION_EMAIL": False,
    "SERIALIZERS": {
        "user_create": "authenticator.serializers.UserCreateSerializer",
        "user": "authenticator.serializers.UserCreateSerializer",
        "current_user": "authenticator.serializers.UserCreateSerializer",
        "user_delete": "djoser.serializers.UserDeleteSerializer",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
