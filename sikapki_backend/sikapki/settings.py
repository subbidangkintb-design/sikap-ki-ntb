"""
Django settings for sikapki project.

Semua nilai sensitif (SECRET_KEY, credential database, dsb) diambil dari
environment variable lewat file .env (lihat .env.example untuk daftar
lengkap variabel yang dibutuhkan). File .env TIDAK boleh di-commit ke git.
"""

from pathlib import Path
import environ

# BASE_DIR = folder root project (tempat manage.py berada)
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Environment variables (django-environ)
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
)

# Baca file .env di root project (jika ada). Di production biasanya env
# variable di-set langsung oleh sistem/hosting, bukan lewat file .env.
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    'rest_framework',
    'corsheaders',

    # apps milik SIKAP-KI NTB
    'core',
    'knowledge.apps.KnowledgeConfig',
    'trademark',
    'chatbot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # CorsMiddleware harus diletakkan sepagi mungkin, sebelum CommonMiddleware
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sikapki.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sikapki.wsgi.application'
ASGI_APPLICATION = 'sikapki.asgi.application'

# ---------------------------------------------------------------------------
# Database — PostgreSQL, dikonfigurasi lewat DATABASE_URL di .env
# Contoh: postgres://USER:PASSWORD@HOST:PORT/NAME
# ---------------------------------------------------------------------------
DATABASES = {
    'default': env.db('DATABASE_URL'),
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Makassar'  # WITA — sesuai lokasi Kanwil Kemenkum NTB
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ---------------------------------------------------------------------------
# CORS — supaya frontend React (port terpisah, mis. 5173/3000) bisa akses API
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://localhost:5173',
])

# Diperlukan karena kita pakai SessionAuthentication (cookie-based) —
# supaya browser mengirim cookie session saat frontend React (origin
# berbeda) memanggil API ini.
CORS_ALLOW_CREDENTIALS = True

# Django >= 4 mewajibkan origin frontend juga didaftarkan sebagai trusted
# origin untuk proteksi CSRF pada request non-GET (POST/PUT/DELETE, dst).
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ---------------------------------------------------------------------------
# Provider AI untuk chatbot RAG dan AI Cek Merek
# AI_PROVIDER: ollama | gemini | deepseek
# ---------------------------------------------------------------------------
AI_PROVIDER = env('AI_PROVIDER', default='ollama')
AI_MODEL = env('AI_MODEL', default=env('OLLAMA_MODEL', default='qwen2.5'))

OLLAMA_BASE_URL = env('OLLAMA_BASE_URL', default='http://localhost:11434')
OLLAMA_MODEL = env('OLLAMA_MODEL', default=AI_MODEL)

GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_BASE_URL = env('GEMINI_BASE_URL', default='https://generativelanguage.googleapis.com')

DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default='')
DEEPSEEK_BASE_URL = env('DEEPSEEK_BASE_URL', default='https://api.deepseek.com')
