import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "mirror.funmig.com,localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "apps.core", "apps.artifacts", "apps.storage", "apps.pypi_mirror", "apps.npm_mirror",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"), "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
                         "USER": os.getenv("DB_USER", ""), "PASSWORD": os.getenv("DB_PASSWORD", ""), "HOST": os.getenv("DB_HOST", ""), "PORT": os.getenv("DB_PORT", "")}}
LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_TZ = "fa", "Asia/Tehran", True, True
STATIC_URL, STATIC_ROOT = "/static/", BASE_DIR / "staticfiles"
STATICFILES_DIRS = [("vazir", BASE_DIR / "vazir-font-v16.1.0")]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = ["https://mirror.funmig.com"]
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

MIRROR_DOMAIN = os.getenv("MIRROR_DOMAIN", "mirror.funmig.com")
MIRROR_STORAGE_ROOT = Path(os.getenv("MIRROR_STORAGE_ROOT", str(BASE_DIR / "local-data")))
MIRROR_BLOBS_ROOT = MIRROR_STORAGE_ROOT / "blobs" / "sha256"
MIRROR_TEMP_ROOT = MIRROR_STORAGE_ROOT / "temp"
MIRROR_REPOSITORY_ROOT = Path(os.getenv("MIRROR_REPOSITORY_ROOT", "/media/arshia/New Volume1/funmig-mirror/repositories"))
GIT_REPOSITORY_ROOT = Path(os.getenv("GIT_REPOSITORY_ROOT", "/media/arshia/New Volume1/git repo"))
PYPI_UPSTREAM = os.getenv("PYPI_UPSTREAM", "https://pypi.org").rstrip("/")
UPSTREAM_MODE = os.getenv("UPSTREAM_MODE", "auto")
STORAGE_LIMITS = {key: int(os.getenv(env, default)) * 1024**3 for key, env, default in [
    ("total", "TOTAL_STORAGE_LIMIT_GB", "500"), ("pypi", "PYPI_STORAGE_LIMIT_GB", "220"),
    ("npm", "NPM_STORAGE_LIMIT_GB", "170"), ("temp", "TEMP_STORAGE_LIMIT_GB", "10"),
    ("min_free", "MIN_FREE_DISK_GB", "25"),
]}
STORAGE_WATERMARKS = {key: int(os.getenv(env, default)) for key, env, default in [("warning", "STORAGE_WARNING_PERCENT", "80"), ("critical", "STORAGE_CRITICAL_PERCENT", "90"), ("emergency", "STORAGE_EMERGENCY_PERCENT", "95")]}
