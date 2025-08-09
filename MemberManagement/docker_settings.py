"""
Django Docker settings for MemberManagement project.
Reads all relevant setting from the environment
"""

from .settings import *

# No Debugging
DEBUG = False

# show a warning that this is not a real site
ENABLE_DEVEL_WARNING = os.environ.setdefault("DJANGO_ENABLE_DEVEL_WARNING", "") == "1"

# we want to allow all hosts
ALLOWED_HOSTS = os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.setdefault("DJANGO_CSRF_ORIGINS", "").split(",")

# all our sessions be safe
SECRET_KEY = os.environ.setdefault("DJANGO_SECRET_KEY", "")

FINALIZE_AUTOMATICALLY = os.environ.setdefault("FINALIZE_AUTOMATICALLY", "") == "1"

# Passwords
DATABASES = {
    "default": {
        "ENGINE": os.environ.setdefault("DJANGO_DB_ENGINE", ""),
        "NAME": os.environ.setdefault("DJANGO_DB_NAME", ""),
        "USER": os.environ.setdefault("DJANGO_DB_USER", ""),
        "PASSWORD": os.environ.setdefault("DJANGO_DB_PASSWORD", ""),
        "HOST": os.environ.setdefault("DJANGO_DB_HOST", ""),
        "PORT": os.environ.setdefault("DJANGO_DB_PORT", ""),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.environ.setdefault("REDIS_HOST", "redis"),
                    int(os.environ.setdefault("REDIS_PORT", "6379")),
                )
            ],
        },
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.setdefault("EMAIL_HOST", "")
EMAIL_HOST_USER = os.environ.setdefault("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.setdefault("EMAIL_HOST_PASSWORD", "")
EMAIL_FROM = os.environ.setdefault(
    "EMAIL_FROM", "Alumni Association Portal <portal@jacobs-alumni.de>"
)

# staticfiles
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# add the stripe keys
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# set the fixer access key
FIXER_ACCESS_KEY = os.environ.get("FIXER_ACCESS_KEY")

# update the client ID for Google login
GSUITE_OAUTH_CLIENT_ID = os.environ.setdefault("GSUITE_OAUTH_CLIENT_ID", "")

# add the static file root
STATIC_ROOT = "/var/www/static/"

# set the media root
MEDIA_ROOT = os.environ.setdefault("MEDIA_ROOT", "/data/media")

# Sentry
if os.environ.get("DJANGO_RAVEN_DSN"):
    # add sentry
    INSTALLED_APPS += ("raven.contrib.django.raven_compat",)

    import os
    import raven

    RAVEN_CONFIG = {"dsn": os.environ.get("DJANGO_RAVEN_DSN")}


# Donation receipts
PDF_RENDER_SERVER = os.environ.get("PDF_RENDER_SERVER")
SIGNATURE_IMAGE = os.path.join(BASE_DIR, os.environ.setdefault("SIGNATURE_IMAGE", ""))


STRIPE_CONTRIBUTOR_PRICE_ID = os.environ.get("STRIPE_CONTRIBUTOR_PRICE_ID")
STRIPE_PATRON_PRICE_ID = os.environ.get("STRIPE_PATRON_PRICE_ID")
STRIPE_STARTER_PRICE_ID = os.environ.get("STRIPE_STARTER_PRICE_ID")

STRIPE_CONTRIBUTOR_PRODUCT_ID = os.environ.get("STRIPE_CONTRIBUTOR_PRODUCT_ID")
STRIPE_PATRON_PRODUCT_ID = os.environ.get("STRIPE_PATRON_PRODUCT_ID")
STRIPE_STARTER_PRODUCT_ID = os.environ.get("STRIPE_STARTER_PRODUCT_ID")
