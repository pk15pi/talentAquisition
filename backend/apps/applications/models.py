import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

# Rejected and withdrawn rows stay in history and free the candidate+JD slot.
TERMINAL_APPLICATION_STATUSES = ("REJECTED", "WITHDRAWN")


class Application(models.Model):
    class Status(models.TextChoices):
        IDENTIFIED = "IDENTIFIED", "Identified"
        CONTACTED = "CONTACTED", "Contacted"
        INTERESTED = "INTERESTED", "Interested"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        SUBMITTED = "SUBMITTED", "Submitted"
        CLIENT_REVIEW = "CLIENT_REVIEW", "Client Review"
        INTERVIEW = "INTERVIEW", "Interview"
        SELECTED = "SELECTED", "Selected"
        OFFERED = "OFFERED", "Offered"
        JOINED = "JOINED", "Joined"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_code = models.CharField(max_length=30, unique=True, blank=True)
    candidate = models.ForeignKey("candidates.Candidate", on_delete=models.PROTECT, related_name="applications")
    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, related_name="applications")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managed_applications")
    sourced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sourced_applications",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.IDENTIFIED)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    contacted_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    selected_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                condition=~Q(status__in=TERMINAL_APPLICATION_STATUSES),
                name="one_active_application_per_candidate_job",
            ),
            models.CheckConstraint(
                condition=Q(match_score__isnull=True) | Q(match_score__gte=0, match_score__lte=100),
                name="application_match_score_range",
            ),
        ]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["recruiter", "status"]),
            models.Index(fields=["candidate", "status"]),
        ]
        permissions = [
            ("view_all_applications", "Can view all applications"),
        ]

    def save(self, *args, **kwargs):
        if not self.application_code:
            from apps.organizations.utils import next_business_code

            self.application_code = next_business_code("application", "SW-APP-", 5)
        super().save(*args, **kwargs)

    @property
    def is_terminal(self):
        return self.status in TERMINAL_APPLICATION_STATUSES


class ApplicationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=25, blank=True)
    new_status = models.CharField(max_length=25)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    remarks = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
