"""Apply the retention numbers an administrator has saved.

A null period skips that category. There is no default period in code.

What is removed follows the field name and the foreign keys already on the
models. Rows another record protects are left in place and counted as
skipped. This is not an archive, and it does not anonymize a profile that
still has an application. Whether a broader hard-delete ban was intended is
still an open question; protected rows are not forced through it.

- Audit logs older than ``audit_log_retention_days`` are deleted. Nothing
  references them.
- Resumes older than ``resume_retention_days`` are deleted only when no
  submission references them. The stored file is deleted with the row.
- Applications older than ``application_retention_days`` are deleted only
  when no interview, submission, or placement references them. History rows
  cascade with the application.
- Candidates older than ``candidate_retention_days`` are deleted only when
  no application references them. An alias (``merged_into`` set) is kept,
  and so is a survivor that still has aliases, because the merge rule is to
  retain that row.

The cutoff is ``created_at`` for candidates and applications, ``uploaded_at``
for resumes, and ``timestamp`` for audit logs.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.audit.services import record_audit
from apps.candidates.models import Candidate, Resume
from apps.interviews.models import Interview
from apps.placements.models import Placement
from apps.recruitment.models import Submission

from .models import SystemConfiguration


def _cutoff(now, days):
    if days is None:
        return None
    return now - timedelta(days=days)


def _delete_queryset(queryset):
    deleted = 0
    skipped = 0
    for row in queryset.iterator():
        try:
            with transaction.atomic():
                if isinstance(row, Resume) and row.file:
                    row.file.delete(save=False)
                row.delete()
            deleted += 1
        except ProtectedError:
            skipped += 1
    return deleted, skipped


def enforce_retention(*, now=None):
    config = SystemConfiguration.load()
    now = now or timezone.now()
    summary = {
        "enforced": False,
        "candidate_retention_days": config.candidate_retention_days,
        "application_retention_days": config.application_retention_days,
        "resume_retention_days": config.resume_retention_days,
        "audit_log_retention_days": config.audit_log_retention_days,
        "deleted": {},
        "skipped": {},
    }
    periods = (
        config.candidate_retention_days,
        config.application_retention_days,
        config.resume_retention_days,
        config.audit_log_retention_days,
    )
    if all(value is None for value in periods):
        return summary

    summary["enforced"] = True
    resume_cutoff = _cutoff(now, config.resume_retention_days)
    if resume_cutoff is not None:
        protected_resume = Submission.objects.filter(resume_id=OuterRef("pk"))
        resumes = Resume.objects.filter(uploaded_at__lt=resume_cutoff).exclude(Exists(protected_resume))
        deleted, skipped = _delete_queryset(resumes)
        summary["deleted"]["resumes"] = deleted
        summary["skipped"]["resumes"] = skipped

    application_cutoff = _cutoff(now, config.application_retention_days)
    if application_cutoff is not None:
        applications = (
            Application.objects.filter(created_at__lt=application_cutoff)
            .exclude(Exists(Interview.objects.filter(application_id=OuterRef("pk"))))
            .exclude(Exists(Submission.objects.filter(application_id=OuterRef("pk"))))
            .exclude(Exists(Placement.objects.filter(application_id=OuterRef("pk"))))
        )
        deleted, skipped = _delete_queryset(applications)
        summary["deleted"]["applications"] = deleted
        summary["skipped"]["applications"] = skipped

    candidate_cutoff = _cutoff(now, config.candidate_retention_days)
    if candidate_cutoff is not None:
        candidates = (
            Candidate.objects.filter(created_at__lt=candidate_cutoff, merged_into__isnull=True)
            .exclude(Exists(Application.objects.filter(candidate_id=OuterRef("pk"))))
            .exclude(Exists(Candidate.objects.filter(merged_into_id=OuterRef("pk"))))
        )
        deleted, skipped = _delete_queryset(candidates)
        summary["deleted"]["candidates"] = deleted
        summary["skipped"]["candidates"] = skipped

    audit_cutoff = _cutoff(now, config.audit_log_retention_days)
    if audit_cutoff is not None:
        deleted_count, _ = AuditLog.objects.filter(timestamp__lt=audit_cutoff).delete()
        summary["deleted"]["audit_logs"] = deleted_count

    record_audit(
        user=None,
        action="retention_enforced",
        entity_type="organizations.SystemConfiguration",
        entity_id=config.pk,
        details=summary,
    )
    return summary
