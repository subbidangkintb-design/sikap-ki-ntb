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
    'core.apps.CoreConfig',
    'knowledge.apps.KnowledgeConfig',
    'trademark',
    'chatbot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # CorsMiddleware harus diletakkan sepagi mungkin, sebelum CommonMiddleware
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.AdminAuditMiddleware',
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
# Database - PostgreSQL, dikonfigurasi lewat DATABASE_URL di .env
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
TIME_ZONE = 'Asia/Makassar'  # WITA - sesuai lokasi Kanwil Kementerian Hukum NTB
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
# Untuk demo/local LAN tanpa reverse proxy. Pada deployment publik, set False
# dan layani STATIC_ROOT melalui Nginx/Apache/CDN.
SERVE_STATIC_FILES = env.bool('SERVE_STATIC_FILES', default=True)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Unggahan logo publik hanya dibaca di memori dan dibatasi 5 MB. File yang
# disimpan di MEDIA_ROOT hanyalah etiket referensi yang dimasukkan oleh admin.
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
# File yang lebih besar dari ambang ini otomatis ditulis ke temporary file,
# sehingga PDF besar tidak memenuhi RAM selama proses upload.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
MAX_DOCUMENT_UPLOAD_SIZE = env.int(
    'MAX_DOCUMENT_UPLOAD_SIZE', default=100 * 1024 * 1024,
)
MAX_DOCUMENT_TEXT_CHARS = env.int('MAX_DOCUMENT_TEXT_CHARS', default=5_000_000)

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
    'DEFAULT_THROTTLE_RATES': {
        'chatbot': env('CHATBOT_RATE_LIMIT', default='30/min'),
        'cek_merek': env('TRADEMARK_RATE_LIMIT', default='20/min'),
        'uji_pengguna': env('USER_TEST_RATE_LIMIT', default='10/hour'),
    },
}

CHATBOT_MAX_HISTORY_TURNS = env.int('CHATBOT_MAX_HISTORY_TURNS', default=8)
HUMAN_OVERSIGHT_SLA_HOURS = env.int('HUMAN_OVERSIGHT_SLA_HOURS', default=24)
SERVICE_LOG_RETENTION_DAYS = env.int('SERVICE_LOG_RETENTION_DAYS', default=365)
AI_TRADEMARK_CHECK_ENABLED = env.bool('AI_TRADEMARK_CHECK_ENABLED', default=False)
BACKGROUND_JOB_MAX_ATTEMPTS = env.int('BACKGROUND_JOB_MAX_ATTEMPTS', default=3)
BACKGROUND_JOB_POLL_SECONDS = env.int('BACKGROUND_JOB_POLL_SECONDS', default=1)
BACKGROUND_JOB_STALE_MINUTES = env.int('BACKGROUND_JOB_STALE_MINUTES', default=120)
CLASSIFICATION_TOP_K = env.int('CLASSIFICATION_TOP_K', default=3)

# Baseline keamanan. Opsi HTTPS tetap nonaktif pada localhost dan diaktifkan
# lewat environment ketika aplikasi berada di belakang reverse proxy TLS.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
# Probe container berjalan pada loopback HTTP; hanya endpoint ini yang boleh
# melewati redirect karena tidak membawa data sensitif.
SECURE_REDIRECT_EXEMPT = [r'^healthz$']
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)
# Hugging Face/Vercel mengakhiri TLS di reverse proxy. Header ini membuat
# Django tetap mengenali request asal sebagai HTTPS dan mencegah redirect loop.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)

# ---------------------------------------------------------------------------
# CORS - supaya frontend React (port terpisah, mis. 5173/3000) bisa akses API
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://localhost:5173',
])

# Diperlukan karena kita pakai SessionAuthentication (cookie-based) -
# supaya browser mengirim cookie session saat frontend React (origin
# berbeda) memanggil API ini.
CORS_ALLOW_CREDENTIALS = True

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=25)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='SIKAP-KI NTB <no-reply@sikapki.ntb>')

# Django >= 4 mewajibkan origin frontend juga didaftarkan sebagai trusted
# origin untuk proteksi CSRF pada request non-GET (POST/PUT/DELETE, dst).
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ---------------------------------------------------------------------------
# Provider AI pendukung Chatbot Helpdesk KI dan Asisten Penelusuran Awal Merek
# AI_PROVIDER: ollama | gemini | deepseek
# ---------------------------------------------------------------------------
AI_PROVIDER = env('AI_PROVIDER', default='gemini')
AI_MODEL = env('AI_MODEL', default=env('OLLAMA_MODEL', default='gemini-3.1-flash-lite'))
AI_FORCE_IPV4 = env.bool('AI_FORCE_IPV4', default=True)
AI_REQUEST_RETRIES = env.int('AI_REQUEST_RETRIES', default=2)
AI_RETRY_BACKOFF_SECONDS = env.float('AI_RETRY_BACKOFF_SECONDS', default=1.0)
AI_FALLBACK_PROVIDER = env('AI_FALLBACK_PROVIDER', default='')
AI_FALLBACK_MODEL = env('AI_FALLBACK_MODEL', default='')

OLLAMA_BASE_URL = env('OLLAMA_BASE_URL', default='http://localhost:11434')
OLLAMA_MODEL = env('OLLAMA_MODEL', default=AI_MODEL)

GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_BASE_URL = env('GEMINI_BASE_URL', default='https://generativelanguage.googleapis.com')
GEMINI_EMBEDDING_MODEL = env('GEMINI_EMBEDDING_MODEL', default='gemini-embedding-2')
GEMINI_EMBEDDING_DIMENSIONS = env.int('GEMINI_EMBEDDING_DIMENSIONS', default=768)
GEMINI_EMBEDDING_BATCH_SIZE = env.int('GEMINI_EMBEDDING_BATCH_SIZE', default=20)
PDF_OCR_WITH_GEMINI = env.bool('PDF_OCR_WITH_GEMINI', default=True)
PDF_OCR_BATCH_PAGES = env.int('PDF_OCR_BATCH_PAGES', default=3)
GEMINI_OCR_MODEL = env('GEMINI_OCR_MODEL', default='gemini-3.1-flash-lite')
PDF_OCR_WITH_GEMINI = env.bool('PDF_OCR_WITH_GEMINI', default=True)
PDF_OCR_BATCH_PAGES = env.int('PDF_OCR_BATCH_PAGES', default=3)
GEMINI_OCR_MODEL = env('GEMINI_OCR_MODEL', default='gemini-3.1-flash-lite')

# Embedding knowledge base. Provider lokal memakai Sentence Transformers
# sehingga indexing dan pencarian tidak mengurangi kuota Gemini.
EMBEDDING_PROVIDER = env('EMBEDDING_PROVIDER', default='gemini')
LOCAL_EMBEDDING_MODEL = env(
    'LOCAL_EMBEDDING_MODEL',
    default='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
)
LOCAL_EMBEDDING_DEVICE = env('LOCAL_EMBEDDING_DEVICE', default='cpu')
LOCAL_EMBEDDING_BATCH_SIZE = env.int('LOCAL_EMBEDDING_BATCH_SIZE', default=16)
LOCAL_EMBEDDING_CACHE = env(
    'LOCAL_EMBEDDING_CACHE', default=str(BASE_DIR / 'embedding_models'),
)
LOCAL_BIAYA_REQUIRED_CONFIDENCE = env.float(
    'LOCAL_BIAYA_REQUIRED_CONFIDENCE', default=0.62,
)
EMBEDDING_CHUNK_SIZE = env.int('EMBEDDING_CHUNK_SIZE', default=500)
EMBEDDING_CHUNK_OVERLAP = env.int('EMBEDDING_CHUNK_OVERLAP', default=50)
CHROMA_COLLECTION_NAME = env('CHROMA_COLLECTION_NAME', default='knowledge_chunks')

DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY', default='')
DEEPSEEK_BASE_URL = env('DEEPSEEK_BASE_URL', default='https://api.deepseek.com')
DJKI_REQUEST_RETRIES = env.int('DJKI_REQUEST_RETRIES', default=3)
DJKI_RETRY_BACKOFF_SECONDS = env.float('DJKI_RETRY_BACKOFF_SECONDS', default=2.0)


