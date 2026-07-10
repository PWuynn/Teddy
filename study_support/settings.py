from pathlib import Path
import os
from importlib.util import find_spec
from dotenv import load_dotenv
import dj_database_url
import cloudinary


BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path, override=True)
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-m)62+2!_5v$d%qj_h^oy$k7wc#zl-=!s84^%btk5vbz4u%oh+@')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if host.strip()]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
     "cloudinary",
    'accounts',
    'quiz_ai',
    'classroom',
    'courses',
    'todo',
    'materials',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if find_spec('whitenoise') else []),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'study_support.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'study_support.wsgi.application'

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

# PostgreSQL (Neon / Render)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL chưa được thiết lập. Hãy thêm DATABASE_URL vào file .env hoặc Environment Variables."
    )

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


LANGUAGE_CODE = 'en-us'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True
cloudinary.config(
    cloud_name=os.getenv("ujnnuday"),
    api_key=os.getenv("794331186292349"),
    api_secret=os.getenv("_aS_LZh50ma17vQu83vW7jdKzQg"),
    secure=True,
)

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'} if find_spec('whitenoise') else {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]

AUTH_USER_MODEL = 'accounts.CustomUser'
