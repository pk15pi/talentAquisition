import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("synfotalent")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "enforce-retention-daily": {
        "task": "apps.organizations.tasks.enforce_retention",
        "schedule": timedelta(hours=24),
    },
}
