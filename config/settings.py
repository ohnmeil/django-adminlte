"""
Django settings for core project.
"""

import os
import random
import string
from pathlib import Path

from dotenv import load_dotenv
from str2bool import str2bool
from django.utils.translation import gettext_lazy as _

# =========================
# Admin Site Branding
# =========================
ADMIN_SITE_HEADER = "Quản lý công việc"
ADMIN_SITE_TITLE = "O³ Invest"
ADMIN_INDEX_TITLE = "Trang điều khiển"

# Load .env
load_dotenv()

# =========================
# Paths
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# Security / Debug
# =========================
SECRET_KEY = os.environ.get("SECRET_KEY", "Super_Secr3t_9999")
DEBUG = str2bool(os.environ.get("DEBUG"))

# =========================
# Host & CSRF configuration
# =========================
# Bạn có thể set trong .env:
#   APP_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,192.168.1.100
#   APP_PORT=155
#   APP_USE_HTTPS=false
#   BEHIND_PROXY=false
app_allowed_hosts = os.environ.get(
    "APP_ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0,192.168.100.50,113.22.34.118",
)
APP_PORT = os.environ.get("APP_PORT", "155")
APP_USE_HTTPS = str2bool(os.environ.get("APP_USE_HTTPS", "false"))
BEHIND_PROXY = str2bool(os.environ.get("BEHIND_PROXY", "false"))

# Danh sách hosts
ALLOWED_HOSTS = [h.strip() for h in app_allowed_hosts.split(",") if h.strip()]

# Render (nếu dùng)
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Với DEBUG, cho phép * để tiện dev (tuỳ bạn)
if DEBUG and "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")

# CSRF Trusted Origins (Django 4.x yêu cầu scheme + đúng port)
CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    # bỏ wildcard
    if host == "*":
        continue
    # Nếu có scheme sẵn (http/https) thì giữ nguyên
    if host.startswith("http://") or host.startswith("https://"):
        CSRF_TRUSTED_ORIGINS.append(host)
        continue
    # Thêm origin http theo PORT
    CSRF_TRUSTED_ORIGINS.append(f"http://{host}:{APP_PORT}")
    # Nếu bạn dùng https (reverse proxy/ssl terminate), thêm https
    if APP_USE_HTTPS:
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}:{APP_PORT}")

# Nếu chạy sau reverse proxy có SSL terminate, khai báo header này
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Khi chạy HTTPS thực sự mới bật 2 dòng này
if APP_USE_HTTPS:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

# =========================
# Applications
# =========================
INSTALLED_APPS = [
    "jazzmin",
    "admin_adminlte.apps.AdminAdminlteConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "work",

    # Serve UI pages
    "apps.pages",

    # Dynamic DT
    "apps.dyn_dt",

    # Dynamic API
    "apps.dyn_api",

    # Charts
    "apps.charts",

    # Tooling API-GEN
    "rest_framework",
    "rest_framework.authtoken",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

HOME_TEMPLATES = os.path.join(BASE_DIR, "templates")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [HOME_TEMPLATES],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =========================
# Database
# =========================
DB_ENGINE = os.getenv("DB_ENGINE", None)
DB_USERNAME = os.getenv("DB_USERNAME", None)
DB_PASS = os.getenv("DB_PASS", None)
DB_HOST = os.getenv("DB_HOST", None)
DB_PORT = os.getenv("DB_PORT", None)
DB_NAME = os.getenv("DB_NAME", None)

if DB_ENGINE and DB_NAME and DB_USERNAME:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends." + DB_ENGINE,
            "NAME": DB_NAME,
            "USER": DB_USERNAME,
            "PASSWORD": DB_PASS,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "db.sqlite3",
        }
    }

# =========================
# Password validation
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# I18N / TZ
# =========================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =========================
# Static files
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)

# =========================
# Email (dev: console)
# =========================
# Bản gốc của bạn có SMTP Gmail; để an toàn trong dev,
# mình để backend console. Khi cần gửi thật, set ENV & đổi backend.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = str2bool(os.environ.get("EMAIL_USE_TLS", "true"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "yourgmail@gmail.com")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "app_password_16_chars")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# =========================
# Default PK / Auth redirects
# =========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/tien-do-thuc-hien/"
LOGOUT_REDIRECT_URL = "/login/"

# =========================
# Dynamic settings for dyn_dt & dyn_api
# =========================
DYNAMIC_DATATB = {
    "product": "apps.pages.models.Product",
}

DYNAMIC_API = {
    "product": "apps.pages.models.Product",
}

# =========================
# DRF
# =========================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
}

