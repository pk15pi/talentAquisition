import uuid

from django.conf import settings
from django.db import models


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey("applications.Application", on_delete=models.PROTECT, related_name="submissions")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="client_submissions")
    resume = models.ForeignKey("candidates.Resume", on_delete=models.PROTECT)
    submission_date = models.DateTimeField(auto_now_add=True)
    client_feedback = models.TextField(blank=True)
    response_status = models.CharField(max_length=30, default="PENDING")
