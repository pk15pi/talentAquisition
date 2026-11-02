import json

from django.core.management.base import BaseCommand

from apps.organizations.retention import enforce_retention


class Command(BaseCommand):
    help = "Apply saved retention periods. Null periods are skipped."

    def handle(self, *args, **options):
        summary = enforce_retention()
        self.stdout.write(json.dumps(summary, default=str))
