import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CodeSequence(models.Model):
    key = models.CharField(max_length=80, unique=True)
    current_value = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"{self.key}={self.current_value}"


class SystemConfiguration(models.Model):
    """Single row of company settings. Retention periods are null until an admin sets them."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    candidate_retention_days = models.PositiveIntegerField(null=True, blank=True)
    application_retention_days = models.PositiveIntegerField(null=True, blank=True)
    resume_retention_days = models.PositiveIntegerField(null=True, blank=True)
    audit_log_retention_days = models.PositiveIntegerField(null=True, blank=True)
    privacy_notice_version = models.CharField(max_length=64, blank=True)
    privacy_notice_text = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_configuration_updates",
    )

    class Meta:
        verbose_name = "System configuration"
        verbose_name_plural = "System configuration"

    def __str__(self):
        return "System configuration"

    def save(self, *args, **kwargs):
        if self.singleton is not True:
            raise ValidationError("System configuration must stay a single row.")
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(singleton=True)
        return obj
