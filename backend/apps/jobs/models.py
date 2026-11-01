import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Job(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        ON_HOLD = "ON_HOLD", "On Hold"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    class FeeType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage"
        FIXED = "FIXED", "Fixed Amount"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_code = models.CharField(max_length=30, unique=True, blank=True)
    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="jobs")
    title = models.CharField(max_length=255)
    jd_text = models.TextField()
    experience_min = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    experience_max = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    location = models.CharField(max_length=150, blank=True)
    work_mode = models.CharField(
        max_length=20,
        choices=[("OFFICE", "Office"), ("HYBRID", "Hybrid"), ("REMOTE", "Remote")],
        default="OFFICE",
    )
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    positions = models.PositiveIntegerField(default=1)
    notice_period_days = models.PositiveIntegerField(null=True, blank=True)
    fee_type = models.CharField(max_length=15, choices=FeeType.choices, blank=True)
    fee_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    guarantee_period_days = models.PositiveIntegerField(null=True, blank=True)
    sales_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    priority = models.CharField(
        max_length=15,
        choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("URGENT", "Urgent")],
        default="MEDIUM",
    )
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["sales_owner", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(experience_max__gte=F("experience_min")),
                name="job_experience_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(salary_max__isnull=True) | Q(salary_min__isnull=True) | Q(salary_max__gte=F("salary_min")),
                name="job_salary_range_valid",
            ),
            models.CheckConstraint(
                condition=Q(fee_value__isnull=True) | Q(fee_value__gte=0),
                name="job_fee_value_nonnegative",
            ),
        ]
        permissions = [
            ("view_all_jobs", "Can view all job descriptions"),
            ("assign_recruiter", "Can assign recruiters to a job description"),
            ("assign_job_owner", "Can assign the sales owner of a job description"),
            ("run_match", "Can run candidate matching for a job description"),
            ("be_assigned_recruiter", "Can be assigned as a recruiter on a job description"),
        ]

    def save(self, *args, **kwargs):
        if not self.job_code:
            from apps.organizations.utils import next_business_code

            self.job_code = next_business_code("job", "SW-JD-", 4)
        super().save(*args, **kwargs)

    def effective_commercial_terms(self):
        """JD values override client defaults. A blank or null JD field inherits."""
        client = self.client
        return {
            "fee_type": self.fee_type or client.default_fee_type,
            "fee_value": self.fee_value if self.fee_value is not None else client.default_fee_value,
            "guarantee_period_days": (
                self.guarantee_period_days
                if self.guarantee_period_days is not None
                else client.default_guarantee_period_days
            ),
        }

    def __str__(self):
        return f"{self.job_code} - {self.title}"


class JobAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="assignments")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="job_assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job", "recruiter"], name="unique_job_recruiter_assignment")]


class JobAssignmentHistory(models.Model):
    class Action(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Assigned"
        UNASSIGNED = "UNASSIGNED", "Unassigned"
        REACTIVATED = "REACTIVATED", "Reactivated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="assignment_history")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="job_assignment_history")
    action = models.CharField(max_length=20, choices=Action.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="job_assignment_changes")
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)


class JobStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
