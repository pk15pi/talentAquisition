from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.applications.models import Application
from apps.audit.models import AuditLog
from apps.candidates.models import Candidate, CandidateConsent, CandidateMerge, DuplicateReview
from apps.interviews.models import Interview
from apps.matching.models import CandidateSkill, Skill
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class DuplicateMergeTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.survivor = make_candidate(self.hr, email="surv@example.com", phone="9000000001", name="Surviving Person")
        self.alias = make_candidate(self.sales, email="alias@example.com", phone="9000000002", name="Alias Person")
        self.alias.privacy_notice_version = "notice-alias"
        self.alias.save(update_fields=["privacy_notice_version"])
        CandidateConsent.objects.create(
            candidate=self.alias,
            purpose="recruitment",
            processing_basis="consent",
            privacy_notice_version="notice-alias",
            recorded_by=self.sales,
            source="test",
        )
        self.review = DuplicateReview.objects.create(
            candidate=self.alias,
            matched_candidate=self.survivor,
            match_type=DuplicateReview.MatchType.EMAIL,
        )
        self.client_row = make_client(self.sales, "Merge Client")
        self.job = make_job(self.client_row, self.sales, "Merge Role")

    def test_merge_relinks_and_keeps_alias_consent(self):
        application = Application.objects.create(
            candidate=self.alias,
            job=self.job,
            recruiter=self.hr,
            status="IDENTIFIED",
        )
        interview = Interview.objects.create(
            application=application,
            round_name="Screen",
            interview_date=timezone.now(),
            created_by=self.hr,
        )
        skill = Skill.objects.create(name="Python", normalized_name="python-merge")
        CandidateSkill.objects.create(candidate=self.survivor, skill=skill, experience_months=12)
        CandidateSkill.objects.create(candidate=self.alias, skill=skill, experience_months=3)
        survivor_consent = self.survivor.consent_recorded_at
        self.as_user(self.hr)
        response = self.client.post(
            f"/api/v1/duplicate-reviews/{self.review.id}/merge/",
            {"surviving_candidate_id": str(self.survivor.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["merge"]["consent_copied"])
        self.assertFalse(response.data["merge"]["alias_deleted"])
        self.assertTrue(any(item["field"] == "full_name" for item in response.data["merge"]["conflicts"]))
        self.assertTrue(any(item["field"] == "candidate_skill" for item in response.data["merge"]["conflicts"]))
        application.refresh_from_db()
        interview.refresh_from_db()
        self.alias.refresh_from_db()
        self.survivor.refresh_from_db()
        self.assertEqual(application.candidate_id, self.survivor.id)
        self.assertEqual(interview.application_id, application.id)
        self.assertEqual(self.alias.merged_into_id, self.survivor.id)
        self.assertFalse(self.alias.is_active)
        self.assertTrue(Candidate.objects.filter(pk=self.alias.pk).exists())
        self.assertEqual(self.survivor.consent_recorded_at, survivor_consent)
        self.assertEqual(self.survivor.privacy_notice_version, "notice-1")
        self.assertEqual(self.survivor.sourced_by_id, self.hr.id)
        self.assertEqual(self.alias.sourced_by_id, self.sales.id)
        consent = CandidateConsent.objects.get(candidate=self.alias)
        self.assertEqual(consent.privacy_notice_version, "notice-alias")
        self.assertEqual(CandidateSkill.objects.get(candidate=self.survivor, skill=skill).experience_months, 12)
        self.assertEqual(CandidateSkill.objects.get(candidate=self.alias, skill=skill).experience_months, 3)
        self.assertTrue(CandidateMerge.objects.filter(alias_candidate=self.alias, surviving_candidate=self.survivor).exists())
        audit = AuditLog.objects.get(action="candidates_merged")
        self.assertEqual(audit.details["source_candidate_id"], str(self.alias.id))
        self.assertEqual(audit.details["destination_candidate_id"], str(self.survivor.id))
        self.assertEqual(audit.user_id, self.hr.id)
        self.assertFalse(audit.details["consent_copied"])
        self.assertFalse(audit.details["alias_deleted"])

    def test_approve_still_does_not_merge(self):
        self.as_user(self.hr)
        response = self.client.post(
            f"/api/v1/duplicate-reviews/{self.review.id}/decide/",
            {"approved": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.alias.refresh_from_db()
        self.assertIsNone(self.alias.merged_into_id)
        self.assertFalse(CandidateMerge.objects.exists())
        self.assertFalse(AuditLog.objects.get(action="duplicate_review_approved").details["records_merged"])

    def test_same_job_active_applications_abort_the_merge(self):
        Application.objects.create(candidate=self.alias, job=self.job, recruiter=self.hr, status="IDENTIFIED")
        Application.objects.create(candidate=self.survivor, job=self.job, recruiter=self.hr, status="CONTACTED")
        self.as_user(self.hr)
        response = self.client.post(
            f"/api/v1/duplicate-reviews/{self.review.id}/merge/",
            {"surviving_candidate_id": str(self.survivor.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.alias.refresh_from_db()
        self.assertIsNone(self.alias.merged_into_id)
        self.assertEqual(Application.objects.filter(job=self.job).count(), 2)

    def test_rejected_review_and_stranger_profile_are_refused(self):
        self.review.status = DuplicateReview.Status.REJECTED
        self.review.save(update_fields=["status"])
        self.as_user(self.hr)
        refused = self.client.post(
            f"/api/v1/duplicate-reviews/{self.review.id}/merge/",
            {"surviving_candidate_id": str(self.survivor.id)},
            format="json",
        )
        self.assertEqual(refused.status_code, 400, refused.data)
        self.review.status = DuplicateReview.Status.PENDING
        self.review.save(update_fields=["status"])
        other = make_candidate(self.hr, email="other@example.com", phone="9000000003", name="Other")
        stranger = self.client.post(
            f"/api/v1/duplicate-reviews/{self.review.id}/merge/",
            {"surviving_candidate_id": str(other.id)},
            format="json",
        )
        self.assertEqual(stranger.status_code, 400, stranger.data)
        missing = self.client.post("/api/v1/candidates/merge/", {}, format="json")
        self.assertIn(missing.status_code, {404, 405})
        self.assertFalse(CandidateMerge.objects.exists())

    def test_merge_requires_the_duplicate_review_permission(self):
        user = get_user_model().objects.get(pk=self.sales.pk)
        user.groups.clear()
        user.user_permissions.clear()
        user = get_user_model().objects.get(pk=user.pk)
        self.as_user(user)
        response = self.client.post(
            f"/api/v1/duplicate-reviews/{self.review.id}/merge/",
            {"surviving_candidate_id": str(self.survivor.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)


class ConsentWithdrawalTests(SynfoAPITestCase):
    def test_withdrawal_marks_consent_and_does_not_delete(self):
        candidate = make_candidate(self.hr, email="withdraw@example.com", phone="9000000010", name="Withdrawn Person")
        CandidateConsent.objects.create(
            candidate=candidate,
            purpose="recruitment",
            processing_basis="consent",
            privacy_notice_version="notice-1",
            recorded_by=self.hr,
            source="api",
        )
        self.as_user(self.hr)
        response = self.client.post(f"/api/v1/candidates/{candidate.id}/withdraw-consent/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        candidate.refresh_from_db()
        self.assertIsNotNone(candidate.consent_withdrawn_at)
        self.assertIsNotNone(candidate.consent_recorded_at)
        self.assertTrue(Candidate.objects.filter(pk=candidate.pk).exists())
        self.assertIsNotNone(CandidateConsent.objects.get(candidate=candidate).withdrawn_at)
        self.assertTrue(AuditLog.objects.filter(action="consent_withdrawn", entity_id=str(candidate.pk)).exists())
        again = self.client.post(f"/api/v1/candidates/{candidate.id}/withdraw-consent/", {}, format="json")
        self.assertEqual(again.status_code, 400, again.data)

    def test_documented_basis_without_consent_cannot_be_withdrawn(self):
        candidate = Candidate(
            full_name="Contract Basis",
            email="basis@example.com",
            phone="9000000011",
            sourced_by=self.hr,
            privacy_notice_version="notice-1",
        )
        candidate._documented_processing_basis = "contract"
        candidate.save()
        self.assertIsNone(candidate.consent_recorded_at)
        self.as_user(self.hr)
        response = self.client.post(f"/api/v1/candidates/{candidate.id}/withdraw-consent/", {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        candidate.refresh_from_db()
        self.assertIsNone(candidate.consent_withdrawn_at)

    def test_sales_cannot_withdraw_consent(self):
        candidate = make_candidate(self.hr, email="sales-withdraw@example.com", phone="9000000012", name="Hidden Withdraw")
        self.as_user(self.sales)
        response = self.client.post(f"/api/v1/candidates/{candidate.id}/withdraw-consent/", {}, format="json")
        self.assertIn(response.status_code, {403, 404})
