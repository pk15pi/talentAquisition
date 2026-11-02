"""Record withdrawal of consent that was actually given.

A profile stored on a documented non-consent basis has no consent timestamp.
This module does not invent one, and it does not delete the profile,
applications, or resumes. Sourcing attribution is left unchanged.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit

from .models import Candidate


def withdraw_candidate_consent(candidate: Candidate, user, notes: str = "") -> Candidate:
    if not user.has_perm("candidates.change_candidate"):
        raise PermissionDenied("You do not have permission to withdraw candidate consent.")
    if candidate.consent_recorded_at is None:
        raise ValidationError("Consent cannot be withdrawn when none was recorded.")
    if candidate.consent_withdrawn_at is not None:
        raise ValidationError("Consent was already withdrawn.")
    now = timezone.now()
    with transaction.atomic():
        candidate.consent_withdrawn_at = now
        candidate.save(update_fields=["consent_withdrawn_at", "updated_at"])
        marked = candidate.consents.filter(processing_basis="consent", withdrawn_at__isnull=True).update(withdrawn_at=now)
        record_audit(
            user=user,
            action="consent_withdrawn",
            entity_type="candidates.Candidate",
            entity_id=candidate.pk,
            details={
                "consent_recorded_at": candidate.consent_recorded_at.isoformat(),
                "consent_withdrawn_at": now.isoformat(),
                "consent_rows_marked": marked,
                "notes": notes or "",
                "profile_deleted": False,
                "sourced_by_id": str(candidate.sourced_by_id),
            },
        )
    return candidate
