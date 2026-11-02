"""Legal application status moves.

The pipeline advances one step at a time. From any in-progress status the
recruiter may also reject or withdraw. Rejected and withdrawn stay in history
and free the candidate+job slot. Joined does not. Nothing here auto-advances
a row.
"""

from django.db import transaction
from django.utils import timezone

from .models import Application, ApplicationHistory

PIPELINE = (
    Application.Status.IDENTIFIED,
    Application.Status.CONTACTED,
    Application.Status.INTERESTED,
    Application.Status.SHORTLISTED,
    Application.Status.SUBMITTED,
    Application.Status.CLIENT_REVIEW,
    Application.Status.INTERVIEW,
    Application.Status.SELECTED,
    Application.Status.OFFERED,
    Application.Status.JOINED,
)

EXIT_STATUSES = frozenset(
    {
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    }
)


class IllegalStatusTransition(Exception):
    def __init__(self, current, requested, allowed):
        self.current = current
        self.requested = requested
        self.allowed = tuple(sorted(allowed))
        allowed_text = ", ".join(self.allowed) if self.allowed else "none"
        super().__init__(
            f"Cannot move an application from {current} to {requested}. Allowed: {allowed_text}."
        )


def allowed_status_transitions(current: str) -> set[str]:
    if current in EXIT_STATUSES or current == Application.Status.JOINED:
        return set()
    try:
        index = PIPELINE.index(current)
    except ValueError:
        return set()
    allowed = set(EXIT_STATUSES)
    if index + 1 < len(PIPELINE):
        allowed.add(PIPELINE[index + 1])
    return allowed


def change_application_status(application, new_status, user, remarks=""):
    allowed = allowed_status_transitions(application.status)
    if new_status not in allowed:
        raise IllegalStatusTransition(application.status, new_status, allowed)
    old = application.status
    with transaction.atomic():
        application.status = new_status
        if new_status == Application.Status.CONTACTED and not application.contacted_at:
            application.contacted_at = timezone.now()
        if new_status == Application.Status.SUBMITTED:
            application.submitted_at = timezone.now()
        if new_status == Application.Status.SELECTED:
            application.selected_at = timezone.now()
        if new_status == Application.Status.JOINED:
            application.joined_at = timezone.now()
        application.save()
        ApplicationHistory.objects.create(
            application=application,
            old_status=old,
            new_status=new_status,
            changed_by=user,
            remarks=remarks or "",
        )
    return application
