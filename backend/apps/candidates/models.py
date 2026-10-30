import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Candidate(models.Model):
    class Source(models.TextChoices):
        LINKEDIN = "LINKEDIN", "LinkedIn"
        REFERRAL = "REFERRAL", "Referral"
        JOB_PORTAL = "JOB_PORTAL", "Job Portal"
        WEBSITE = "WEBSITE", "Website"
        INTERNAL = "INTERNAL", "Internal"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate_code = models.CharField(max_length=30, unique=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    normalized_email = models.CharField(max_length=254, blank=True)
    phone = models.CharField(max_length=25, blank=True)
    normalized_phone = models.CharField(max_length=25, blank=True)
    current_company = models.CharField(max_length=200, blank=True)
    total_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    current_ctc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_ctc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=150, blank=True)
    notice_period_days = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.OTHER)
    sourced_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sourced_candidates")
    consent_recorded_at = models.DateTimeField()
    privacy_notice_version = models.CharField(max_length=64)
    consent_withdrawn_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_email"]),
            models.Index(fields=["normalized_phone"]),
            models.Index(fields=["location"]),
            models.Index(fields=["sourced_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(privacy_notice_version=""),
                name="candidate_consent_version_present",
            ),
            models.CheckConstraint(
                condition=Q(consent_withdrawn_at__isnull=True) | Q(consent_withdrawn_at__gte=F("consent_recorded_at")),
                name="candidate_consent_withdrawal_after_grant",
            ),
        ]
        permissions = [
            ("review_duplicate", "Can decide a duplicate-candidate review"),
        ]

    def save(self, *args, **kwargs):
        if not self.consent_recorded_at or not (self.privacy_notice_version or "").strip():
            raise ValidationError("Candidate consent and a privacy notice version are required before a profile can be stored.")
        self.privacy_notice_version = self.privacy_notice_version.strip()
        self.normalized_email = (self.email or "").strip().lower()
        self.normalized_phone = "".join(character for character in (self.phone or "") if character.isdigit())
        if not self.candidate_code:
            from apps.organizations.utils import next_business_code

            self.candidate_code = next_business_code("candidate", "SW-CAN-", 5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.candidate_code} - {self.full_name}"


class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to="resumes/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, blank=True)
    parsed_text = models.TextField(blank=True)
    parsing_status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("PROCESSING", "Processing"),
            ("COMPLETED", "Completed"),
            ("FAILED", "Failed"),
        ],
        default="PENDING",
    )
    version = models.PositiveIntegerField(default=1)
    is_primary = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["candidate", "version"], name="unique_candidate_resume_version"),
            models.UniqueConstraint(fields=["candidate"], condition=Q(is_primary=True), name="one_primary_resume_per_candidate"),
        ]
        indexes = [models.Index(fields=["file_hash"])]


class CandidateNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="notes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class CandidateConsent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="consents")
    purpose = models.CharField(max_length=150)
    source = models.CharField(max_length=150, blank=True)
    processing_basis = models.CharField(max_length=100)
    privacy_notice_version = models.CharField(max_length=64, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_candidate_consents",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)


class DuplicateReview(models.Model):
    """A human decision about two candidate rows. Approving does not merge or delete them."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class MatchType(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        PHONE = "PHONE", "Phone"
        FILE_HASH = "FILE_HASH", "File hash"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="duplicate_reviews")
    matched_candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="matched_in_reviews")
    match_type = models.CharField(max_length=20, choices=MatchType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="duplicate_reviews_decided",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "matched_candidate", "match_type"],
                name="unique_duplicate_pair_type",
            ),
            models.CheckConstraint(
                condition=~Q(candidate=F("matched_candidate")),
                name="duplicate_review_distinct_candidates",
            ),
        ]
        indexes = [models.Index(fields=["status", "match_type"])]

    def decide(self, user, approved: bool, notes: str = ""):
        if not user.has_perm("candidates.review_duplicate"):
            raise PermissionDenied("You do not have permission to decide duplicate reviews.")
        if self.status != self.Status.PENDING:
            raise ValidationError("This duplicate review has already been decided.")
        self.status = self.Status.APPROVED if approved else self.Status.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes"])
        from apps.audit.models import AuditLog

        AuditLog.objects.create(
            user=user,
            action="duplicate_review_approved" if approved else "duplicate_review_rejected",
            entity_type="candidates.DuplicateReview",
            entity_id=str(self.pk),
            details={
                "candidate_id": str(self.candidate_id),
                "matched_candidate_id": str(self.matched_candidate_id),
                "match_type": self.match_type,
                "records_merged": False,
            },
        )
