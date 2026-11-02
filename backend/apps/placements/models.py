import uuid

from django.db import models
from django.db.models import Q


class Placement(models.Model):
    class Status(models.TextChoices):
        OFFERED = "OFFERED", "Offered"
        JOINED = "JOINED", "Joined"
        CANCELLED = "CANCELLED", "Cancelled"
        GUARANTEE = "GUARANTEE", "Guarantee Period"
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField("applications.Application", on_delete=models.PROTECT, related_name="placement")
    joining_date = models.DateField(null=True, blank=True)
    offered_ctc = models.DecimalField(max_digits=12, decimal_places=2)
    agreed_fee_type = models.CharField(max_length=15, choices=[("PERCENTAGE", "Percentage"), ("FIXED", "Fixed Amount")])
    agreed_fee_value = models.DecimalField(max_digits=10, decimal_places=2)
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    guarantee_period_days = models.PositiveIntegerField(default=90)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFERED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        application = self.application
        code = application.application_code or ""
        name = application.candidate.full_name if application.candidate_id else ""
        label = " — ".join(part for part in (code, name) if part)
        return label or f"Placement {self.pk}"

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(offered_ctc__gte=0) & Q(agreed_fee_value__gte=0) & Q(expected_revenue__gte=0),
                name="placement_amounts_nonnegative",
            )
        ]
        permissions = [
            ("view_placement_financials", "Can view placement CTC, fees, and expected revenue"),
            ("change_placement_financials", "Can edit placement CTC, fees, and expected revenue"),
        ]
