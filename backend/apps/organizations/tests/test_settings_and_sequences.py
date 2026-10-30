from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.applications.models import Application
from apps.billing.models import CreditNote, Invoice
from apps.interviews.models import Interview
from apps.matching.models import Skill, SkillAlias
from apps.organizations.models import SystemConfiguration
from apps.organizations.utils import next_business_code
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class SettingsAndSequenceTests(SynfoAPITestCase):
    def test_retention_is_empty_until_an_authorized_admin_sets_it(self):
        config = SystemConfiguration.load()
        self.assertIsNone(config.candidate_retention_days)
        self.assertIsNone(config.application_retention_days)
        self.assertIsNone(config.resume_retention_days)
        self.assertIsNone(config.audit_log_retention_days)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SystemConfiguration.objects.create(singleton=True)
        self.as_user(self.hr)
        denied = self.client.patch(
            "/api/v1/system-configuration/",
            {"candidate_retention_days": 30},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.as_user(self.management)
        updated = self.client.patch(
            "/api/v1/system-configuration/",
            {"candidate_retention_days": 400, "privacy_notice_version": "notice-2"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["candidate_retention_days"], 400)
        self.assertEqual(updated.data["privacy_notice_version"], "notice-2")

    def test_business_codes_use_the_sequence(self):
        self.assertEqual(next_business_code("job", "SW-JD-", 4), "SW-JD-0001")
        self.assertEqual(next_business_code("job", "SW-JD-", 4), "SW-JD-0002")
        self.assertEqual(next_business_code("candidate", "SW-CAN-", 5), "SW-CAN-00001")
        client = make_client(self.sales)
        job = make_job(client, self.sales)
        self.assertTrue(client.client_code.startswith("SW-CLI-"))
        self.assertTrue(job.job_code.startswith("SW-JD-"))

    def test_credit_note_number_is_sequenced(self):
        client = make_client(self.management, "Billed")
        invoice = Invoice.objects.create(
            client=client,
            invoice_date=timezone.localdate(),
            due_date=timezone.localdate(),
            created_by=self.management,
        )
        note = CreditNote.objects.create(
            invoice=invoice,
            amount=Decimal("25.00"),
            reason="Adjustment",
            issue_date=timezone.localdate(),
            created_by=self.management,
        )
        year = timezone.localdate().year
        self.assertTrue(note.credit_note_number.startswith(f"SW-CN-{year}-"))

    def test_skill_alias_is_normalized_and_unique(self):
        skill = Skill.objects.create(name="JavaScript", normalized_name="javascript")
        SkillAlias.objects.create(skill=skill, alias="JS")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SkillAlias.objects.create(skill=skill, alias="js")

    def test_reschedule_is_kept_as_history(self):
        candidate = make_candidate(self.hr, email="iv@example.com", phone="9555555555")
        job = make_job(make_client(self.sales, "Interview Co"), self.sales, "Interview JD")
        application = Application.objects.create(candidate=candidate, job=job, recruiter=self.hr)
        when = timezone.now()
        interview = Interview.objects.create(
            application=application,
            round_name="L1",
            interview_date=when,
            feedback="Keep private",
            created_by=self.hr,
        )
        self.assertTrue(interview.events.filter(event_type="CREATED").exists())
        interview.interview_date = when + timedelta(days=2)
        interview._changed_by = self.hr
        interview.save()
        self.assertTrue(interview.events.filter(event_type="RESCHEDULED").exists())
        self.as_user(self.sales)
        hidden = self.client.get("/api/v1/interviews/")
        self.assertEqual(hidden.status_code, 403)
        self.as_user(self.hr)
        visible = self.client.get("/api/v1/interviews/")
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(visible.data["results"][0]["feedback"], "Keep private")
