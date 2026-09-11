"""
Django settings for the CommUnity project.

Every deployment-specific value is read from environment variables (or a `.env`
file next to manage.py) so the same code runs on a laptop with SQLite and in
production with MySQL. See `.env.example` for the full list.
"""

from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent


# --- Core -----------------------------------------------------------------

SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-cizxr8o2i(+dx2v+k&x4s+$)9flfn8y#0xvk_%+#3+-xn)7trf',
)
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Public base URL, used to build absolute links inside e-mails.
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000').rstrip('/')
COLLEGE_NAME = config('COLLEGE_NAME', default='KJSIT')


# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'Login',
    'events',
    'faculty',
    'home',
    'members',
    'committees',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'CommUnity.urls'

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
                'Login.context_processors.community',
            ],
        },
    },
]

WSGI_APPLICATION = 'CommUnity.wsgi.application'


# --- Database ---------------------------------------------------------------
# DB_ENGINE=mysql switches to MySQL; anything else keeps the bundled SQLite file.

DB_ENGINE = config('DB_ENGINE', default='sqlite').lower()

if DB_ENGINE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='community'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config('SQLITE_PATH', default=str(BASE_DIR / 'db.sqlite3')),
        }
    }


# --- Auth -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'Login.CustomUser'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'

# Only institutional addresses may sign up or sign in.
ALLOWED_EMAIL_DOMAINS = config('ALLOWED_EMAIL_DOMAINS', default='somaiya.edu', cast=Csv())

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_FORMS = {
    'signup': 'Login.forms.CustomSignUpForm',
    'login': 'Login.forms.CustomLoginForm',
}
ACCOUNT_ADAPTER = 'Login.account_adapter.MyAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'Login.social_adapter.MySocialAccountAdapter'

GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

_google_provider = {
    'SCOPE': ['profile', 'email'],
    'AUTH_PARAMS': {'hd': ALLOWED_EMAIL_DOMAINS[0] if ALLOWED_EMAIL_DOMAINS else ''},
}
# Without credentials the Google button is hidden instead of failing at runtime.
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    _google_provider['APP'] = {
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'key': '',
    }
SOCIALACCOUNT_PROVIDERS = {'google': _google_provider}


# --- Internationalization ---------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# --- Static & media ---------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- E-mail -----------------------------------------------------------------
# Falls back to printing e-mails in the console until SMTP details are provided.

EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST_USER
    else 'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'CommUnity <noreply@community.local>')


# --- Google Calendar --------------------------------------------------------

GOOGLE_SERVICE_ACCOUNT_FILE = config(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    default=str(BASE_DIR / 'community-450615-ea7ca3c3bfa3.json'),
)
# Also accept the variable name used by earlier versions of the project.
GOOGLE_CALENDAR_ID = config('GOOGLE_CALENDAR_ID', default=config('CALENDAR_ID', default=''))


# --- Generative AI (post-event reports) -------------------------------------
# AI_PROVIDER: auto | anthropic | huggingface | template
#   auto picks Claude when ANTHROPIC_API_KEY is set, then Hugging Face, and
#   otherwise builds a structured draft offline so the feature always works.

AI_PROVIDER = config('AI_PROVIDER', default='auto').lower()
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
AI_MODEL = config('AI_MODEL', default='claude-opus-5')
HUGGINGFACE_API_KEY = config('HUGGINGFACE_API_KEY', default='')
HUGGINGFACE_MODEL = config('HUGGINGFACE_MODEL', default='meta-llama/Llama-3.1-8B-Instruct')


# --- Production hardening ---------------------------------------------------

if not DEBUG:
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
