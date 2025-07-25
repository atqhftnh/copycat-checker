"""
Django settings for PlagiarismGuard project.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from pathlib import Path
import dj_database_url
import logging
import dotenv
import nltk

dotenv.load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_long_random_string_for_local_dev_ONLY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = ['copycat-checker.onrender.com', 'localhost', '127.0.0.1']

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'plag',
    'storages'
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ⭐ NEW: Add LocaleMiddleware here ⭐
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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


ROOT_URLCONF = 'PlagiarismGuard.urls'

WSGI_APPLICATION = 'PlagiarismGuard.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        # Look for a special variable called 'DATABASE_URL'
        # Provide a local SQLite default if DATABASE_URL is not set
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        # Keep database connections alive for a bit
        conn_max_age=600
    )
}

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC' # Keep UTC, recommended for Django projects

USE_I18N = True # Keep True

# USE_L10N = True # Keep True, but note it's deprecated in Django 4.0 (use USE_TZ for datetime formatting)

USE_TZ = True # Keep True, essential for timezone-aware datetimes

PDF_TO_TEXT = os.environ.get('PDF_TO_TEXT_PATH', '/usr/bin/pdftotext')   # Ensure this path is correct and accessible

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/topics/settings/
# https://docs.djangoproject.com/en/4.2/ref/settings/

STATIC_URL = '/static/'
# ADDED STATIC_ROOT for collectstatic (important for deployment)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# AWS S3 Settings for Media Files
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME') # e.g., 'us-east-1'

# Ensure uploaded files are publicly readable (necessary for users to view them)
AWS_DEFAULT_ACL = 'public-read'

# Construct the S3 custom domain for generating URLs
# This assumes your bucket is in the standard S3 domain format
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'

AWS_S3_FILE_OVERWRITE = False

# Tell Django to use S3 for media file storage
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Paths for media (user-uploaded files)
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
MEDIA_ROOT = ''

GOOGLE_SEARCH_API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")   # Google API Key
GOOGLE_SEARCH_ENGINE_ID = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")    #   CSE ID (Custom Search Engine ID)

PLAGIARISM_SETTINGS = {
    'MIN_SIMILARITY_THRESHOLD': 30,   # Minimum similarity percentage to consider
    'MAX_THREADS': 5,   # Max concurrent threads for processing
    'REQUEST_TIMEOUT': 10,  # Seconds before timing out a request
    'CACHE_EXPIRATION': 3600,   # 1 hour cache for API results
    'BLACKLISTED_DOMAINS': [
        'scribd.com', 'slideshare.net', 'academia.edu'
    ],
    'USER_AGENTS': [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ]
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@copycatchecker.com'

NLTK_DATA_PATH = os.environ.get('NLTK_DATA', '')
if NLTK_DATA_PATH and NLTK_DATA_PATH not in nltk.data.path:
    nltk.data.path.append(NLTK_DATA_PATH)

LOGOUT_REDIRECT_URL = '/login/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose', # Use verbose to get more details
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO', # Keep this INFO or DEBUG for general app logs
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Your app's specific loggers (if any)
        'plag': { # Replace 'plag' with your app's name if it has a custom logger
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # *** ADD THESE FOR BOTO3/BOTOCORE DEBUGGING ***
        'boto3': {
            'handlers': ['console'],
            'level': 'DEBUG', # This is key
            'propagate': False,
        },
        'botocore': {
            'handlers': ['console'],
            'level': 'DEBUG', # This is also key
            'propagate': False,
        },
        # You might also want to debug django-storages itself
        'storages': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
