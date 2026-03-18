import os

from celery import Celery


# I set the default Django settings module so Celery can read project settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# I create the main Celery application instance.
app = Celery("config")

# I load Celery settings from Django settings using the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# I automatically discover tasks.py files inside installed Django apps.
app.autodiscover_tasks()