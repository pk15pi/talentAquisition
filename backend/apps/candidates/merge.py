"""Merge two candidate rows that a duplicate review already linked.

The rules in ``reviews.py`` are applied as written:

- The caller names the surviving profile. It must be one of the two people
  on the review. Same-name pairs are never merged, because a review exists
  only for email, phone, or file hash.
- ``sourced_by``, ``source``, and consent rows stay on the person they were
  recorded for. Consent timestamps are not copied onto the survivor.
- Applications are relinked to the survivor. Interviews, submissions, and
  placements point at the application, so they move with it. If both people
  have a non-terminal application for the same job, the merge is aborted
  and nothing is rewritten.
- Resumes move to the survivor. A version or primary-flag collision keeps
  both files by assigning the next version and clearing the extra primary.
- Notes move. A skill the survivor already has stays on the alias and is
  recorded as a conflict. Match results that would duplicate a run stay put.
- The other row remains, inactive, with ``merged_into`` set. It is not deleted.
- Field conflicts are stored on ``CandidateMerge``. Differing values are not
  copied onto the survivor.
- ``AuditLog`` records the actor, time, source (alias), and destination.

Who may merge is not decided (audit open question 9). This uses the existing
``candidates.review_duplicate`` permission. ``decide()`` still does not merge.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.applications.models import TERMINAL_APPLICATION_STATUSES
from apps.audit.services import record_audit
from apps.matching.models import MatchResult

from .models import Candidate, CandidateMerge, DuplicateReview

COMPARE_FIELDS = (
    "full_name",
    "email",
    "phone",
    "current_company",
    "total_experience",
    "current_ctc",
    "expected_ctc",
    "location",
    "notice_period_days",
    "source",
)


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _provenance(candidate: Candidate):
    return {
        "candidate_id": str(candidate.pk),
        "sourced_by_id": str(candidate.sourced_by_id),
        "source": candidate.source,
        "consent_recorded_at": candidate.consent_recorded_at.isoformat() if candidate.consent_recorded_at else None,
        "consent_withdrawn_at": candidate.consent_withdrawn_at.isoformat() if candidate.consent_withdrawn_at else None,
        "privacy_notice_version": candidate.privacy_notice_version,
        "consent_row_ids": [str(row_id) for row_id in candidate.consents.values_list("pk", flat=True)],
    }


def merge_duplicate_review(review: DuplicateReview, user, surviving_candidate_id, notes: str = "") -> CandidateMerge:
    if not user.has_perm("candidates.review_duplicate"):
        raise PermissionDenied("You do not have permission to merge duplicate profiles.")
    if review.status == DuplicateReview.Status.REJECTED:
        raise ValidationError("A rejected duplicate review cannot be merged.")
    if review.merges.exists():
        raise ValidationError("This duplicate review has already been merged.")
    pair = {review.candidate_id, review.matched_candidate_id}
    try:
        surviving_id = review.candidate_id.__class__(str(surviving_candidate_id))
    except (TypeError, ValueError) as exc:
        raise ValidationError("Choose the surviving profile from the two people on this review.") from exc
    if surviving_id not in pair:
        raise ValidationError("The surviving profile must be one of the two people on this review.")
    alias_id = (pair - {surviving_id}).pop()
    now = timezone.now()
    with transaction.atomic():
        locked = DuplicateReview.objects.select_for_update().select_related("candidate", "matched_candidate").get(pk=review.pk)
        if locked.status == DuplicateReview.Status.REJECTED or locked.merges.exists():
            raise ValidationError("This duplicate review can no longer be merged.")
        survivor = Candidate.objects.select_for_update().get(pk=surviving_id)
        alias = Candidate.objects.select_for_update().get(pk=alias_id)
        if survivor.merged_into_id or alias.merged_into_id:
            raise ValidationError("A profile that is already an alias cannot be merged again.")
        active_alias_jobs = set(
            alias.applications.exclude(status__in=TERMINAL_APPLICATION_STATUSES).values_list("job_id", flat=True)
        )
        active_survivor_jobs = set(
            survivor.applications.exclude(status__in=TERMINAL_APPLICATION_STATUSES).values_list("job_id", flat=True)
        )
        if active_alias_jobs & active_survivor_jobs:
            raise ValidationError(
                "Both profiles have an active application for the same job. The merge was not applied."
            )
        conflicts = []
        for field in COMPARE_FIELDS:
            surviving_value = _text(getattr(survivor, field))
            alias_value = _text(getattr(alias, field))
            if surviving_value != alias_value and (surviving_value or alias_value):
                conflicts.append(
                    {"field": field, "surviving_value": surviving_value, "alias_value": alias_value}
                )
        applications = list(alias.applications.all())
        for application in applications:
            application.candidate = survivor
            application.save(update_fields=["candidate", "updated_at"])
        resumes_moved = 0
        for resume in list(alias.resumes.all()):
            if survivor.resumes.filter(version=resume.version).exists():
                resume.version = (survivor.resumes.order_by("-version").values_list("version", flat=True).first() or 0) + 1
            if resume.is_primary and survivor.resumes.filter(is_primary=True).exists():
                resume.is_primary = False
            resume.candidate = survivor
            resume.save(update_fields=["candidate", "version", "is_primary"])
            resumes_moved += 1
        notes_moved = alias.notes.update(candidate=survivor)
        skills_left = []
        for row in list(alias.candidate_skills.select_related("skill")):
            existing = survivor.candidate_skills.filter(skill_id=row.skill_id).first()
            if existing is not None:
                skills_left.append(str(row.skill_id))
                conflicts.append(
                    {
                        "field": "candidate_skill",
                        "skill_id": str(row.skill_id),
                        "surviving_value": _text(existing.experience_months),
                        "alias_value": _text(row.experience_months),
                    }
                )
                continue
            row.candidate = survivor
            row.save(update_fields=["candidate"])
        match_left = []
        for result in list(MatchResult.objects.filter(candidate=alias)):
            if MatchResult.objects.filter(match_run_id=result.match_run_id, candidate=survivor).exists():
                match_left.append(str(result.pk))
                conflicts.append({"field": "match_result", "match_result_id": str(result.pk)})
                continue
            result.candidate = survivor
            result.save(update_fields=["candidate"])
        provenance = {"surviving": _provenance(survivor), "alias": _provenance(alias)}
        alias.merged_into = survivor
        alias.merged_at = now
        alias.is_active = False
        alias.save(update_fields=["merged_into", "merged_at", "is_active", "updated_at"])
        if locked.status == DuplicateReview.Status.PENDING:
            locked.status = DuplicateReview.Status.APPROVED
            locked.reviewed_by = user
            locked.reviewed_at = now
            if notes:
                locked.notes = notes
            locked.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes"])
        merge = CandidateMerge.objects.create(
            review=locked,
            surviving_candidate=survivor,
            alias_candidate=alias,
            conflicts=conflicts,
            consent_provenance=provenance,
            actor=user,
        )
        record_audit(
            user=user,
            action="candidates_merged",
            entity_type="candidates.CandidateMerge",
            entity_id=merge.pk,
            details={
                "review_id": str(locked.pk),
                "match_type": locked.match_type,
                "source_candidate_id": str(alias.pk),
                "destination_candidate_id": str(survivor.pk),
                "actor_id": str(user.pk),
                "merged_at": now.isoformat(),
                "applications_relinked": len(applications),
                "interviews_follow_applications": True,
                "submissions_follow_applications": True,
                "resumes_relinked": resumes_moved,
                "notes_relinked": notes_moved,
                "skills_left_on_alias": skills_left,
                "match_results_left_on_alias": match_left,
                "consent_copied": False,
                "alias_deleted": False,
                "conflict_fields": [item["field"] for item in conflicts],
            },
        )
        return merge
