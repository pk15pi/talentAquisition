import uuid

from django.conf import settings
from django.db import models


class Interview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey("applications.Application", on_delete=models.PROTECT, related_name="interviews")
    round_name = models.CharField(max_length=100)
    interview_date = models.DateTimeField()
    interviewer_name = models.CharField(max_length=150, blank=True)
    feedback = models.TextField(blank=True)
    result = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("PASSED", "Passed"),
            ("FAILED", "Failed"),
            ("ON_HOLD", "On Hold"),
        ],
        default="PENDING",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interviews_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["interview_date"])]
        permissions = [
            ("view_all_interviews", "Can view all interviews"),
        ]

    def save(self, *args, **kwargs):
        previous = None
        if not self._state.adding:
            previous = type(self).objects.filter(pk=self.pk).values_list("interview_date", "result").first()
        super().save(*args, **kwargs)
        actor = getattr(self, "_changed_by", None) or self.created_by
        if previous is None:
            InterviewEvent.objects.create(
                interview=self,
                event_type=InterviewEvent.EventType.CREATED,
                changed_by=actor,
                new_value={"interview_date": self.interview_date.isoformat(), "result": self.result},
            )
            return
        old_date, old_result = previous
        if old_date != self.interview_date:
            InterviewEvent.objects.create(
                interview=self,
                event_type=InterviewEvent.EventType.RESCHEDULED,
                changed_by=actor,
                old_value={"interview_date": old_date.isoformat()},
                new_value={"interview_date": self.interview_date.isoformat()},
            )
        if old_result != self.result:
            InterviewEvent.objects.create(
                interview=self,
                event_type=InterviewEvent.EventType.RESULT_CHANGED,
                changed_by=actor,
                old_value={"result": old_result},
                new_value={"result": self.result},
            )


class InterviewParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interview_participations",
    )
    name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["interview", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_interview_participant_user",
            )
        ]


class InterviewEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        RESCHEDULED = "RESCHEDULED", "Rescheduled"
        RESULT_CHANGED = "RESULT_CHANGED", "Result changed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="interview_events_made",
    )
    created_at = models.DateTimeField(auto_now_add=True)
