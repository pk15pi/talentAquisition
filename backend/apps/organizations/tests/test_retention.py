from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.candidates.models import Resume
from apps.interviews.models import Interview
from apps.organizations.models import SystemConfiguration
from apps.organizations.retention import enforce_retention
from apps.recruitment.models import Submission
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class RetentionEnforcementTests(SynfoAPITestCase):
    def test_null_periods_delete_nothing(self):
        candidate = make_candidate(self.hr, email="keep@example.com", phone="9100000001", name="Keep")
        summary = enforce_retention()
        self.assertFalse(summary["enforced"])
        self.assertTrue(type(candidate).objects.filter(pk=candidate.pk).exists())
        self.assertFalse(AuditLog.objects.filter(action="retention_enforced").exists())

    def test_old_unprotected_rows_are_removed_and_protected_rows_stay(self):
        old = timezone.now() - timedelta(days=400)
        config = SystemConfiguration.load()
        config.candidate_retention_days = 30
        config.application_retention_days = 30
        config.resume_retention_days = 30
        config.audit_log_retention_days = 30
        config.save()

        stale = make_candidate(self.hr, email="stale@example.com", phone="9100000002", name="Stale")
        protected = make_candidate(self.hr, email="protected@example.com", phone="9100000003", name="Protected")
        alias = make_candidate(self.hr, email="alias-ret@example.com", phone="9100000004", name="Alias Ret")
        fresh = make_candidate(self.hr, email="fresh@example.com", phone="9100000005", name="Fresh")
        type(stale).objects.filter(pk__in=[stale.pk, protected.pk, alias.pk]).update(created_at=old)
        alias.merged_into = fresh
        alias.save(update_fields=["merged_into"])

        client = make_client(self.sales, "Retention Client")
        job = make_job(client, self.sales, "Retention Role")
        held = Application.objects.create(candidate=protected, job=job, recruiter=self.hr, status="IDENTIFIED")
        loose = Application.objects.create(candidate=fresh, job=make_job(client, self.sales, "Other Role"), recruiter=self.hr, status="REJECTED")
        Application.objects.filter(pk__in=[held.pk, loose.pk]).update(created_at=old)
        Interview.objects.create(application=held, round_name="Screen", interview_date=timezone.now(), created_by=self.hr)

        loose_resume = Resume.objects.create(
            candidate=fresh,
            file=SimpleUploadedFile("old.pdf", b"%PDF-1.4 old"),
            original_filename="old.pdf",
            version=1,
            uploaded_by=self.hr,
        )
        held_resume = Resume.objects.create(
            candidate=fresh,
            file=SimpleUploadedFile("held.pdf", b"%PDF-1.4 held"),
            original_filename="held.pdf",
            version=2,
            uploaded_by=self.hr,
        )
        Resume.objects.filter(pk__in=[loose_resume.pk, held_resume.pk]).update(uploaded_at=old)
        Submission.objects.create(application=held, submitted_by=self.hr, resume=held_resume)

        stale_log = AuditLog.objects.create(user=self.hr, action="old_event", entity_type="test", entity_id="1")
        AuditLog.objects.filter(pk=stale_log.pk).update(timestamp=old)

        summary = enforce_retention()
        self.assertTrue(summary["enforced"])
        self.assertGreaterEqual(summary["deleted"].get("candidates", 0), 1)
        self.assertFalse(type(stale).objects.filter(pk=stale.pk).exists())
        self.assertTrue(type(protected).objects.filter(pk=protected.pk).exists())
        self.assertTrue(type(alias).objects.filter(pk=alias.pk).exists())
        self.assertTrue(type(fresh).objects.filter(pk=fresh.pk).exists())
        self.assertFalse(Application.objects.filter(pk=loose.pk).exists())
        self.assertTrue(Application.objects.filter(pk=held.pk).exists())
        self.assertFalse(Resume.objects.filter(pk=loose_resume.pk).exists())
        self.assertTrue(Resume.objects.filter(pk=held_resume.pk).exists())
        self.assertFalse(AuditLog.objects.filter(pk=stale_log.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="retention_enforced").exists())
