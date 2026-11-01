from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.candidates.models import Candidate, DuplicateReview
from apps.candidates.reviews import queue_identity_duplicate_reviews
from apps.organizations.models import SystemConfiguration
from apps.testkit import SynfoAPITestCase, make_candidate


class ConsentAndDuplicateTests(SynfoAPITestCase):
    def test_profile_requires_consent(self):
        with self.assertRaises(ValidationError):
            Candidate.objects.create(full_name="No Consent", sourced_by=self.hr)
        self.as_user(self.hr)
        denied = self.client.post(
            "/api/v1/candidates/",
            {"full_name": "No", "email": "no@example.com", "consent_acknowledged": False},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(denied.data["code"], "invalid")
        created = self.client.post(
            "/api/v1/candidates/",
            {
                "full_name": "Yes",
                "email": "yes@example.com",
                "consent_acknowledged": True,
                "privacy_notice_version": "notice-1",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(created.data["candidate_code"].startswith("SW-CAN-"))
        self.assertEqual(Candidate.objects.get(pk=created.data["id"]).consents.count(), 1)

    def test_consent_must_match_configured_notice_version(self):
        config = SystemConfiguration.load()
        config.privacy_notice_version = "notice-9"
        config.save()
        self.as_user(self.hr)
        wrong = self.client.post(
            "/api/v1/candidates/",
            {"full_name": "Wrong", "consent_acknowledged": True, "privacy_notice_version": "notice-1"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)
        right = self.client.post(
            "/api/v1/candidates/",
            {"full_name": "Right", "consent_acknowledged": True, "privacy_notice_version": "notice-9"},
            format="json",
        )
        self.assertEqual(right.status_code, 201, right.data)

    def test_duplicate_review_does_not_merge_and_is_audited(self):
        first = make_candidate(self.hr, email="dup@example.com", phone="9111111111", name="First")
        second = make_candidate(self.hr, email="DUP@example.com", phone="8222222222", name="Second")
        queue_identity_duplicate_reviews(second)
        review = DuplicateReview.objects.get(candidate=second, matched_candidate=first)
        self.assertEqual(review.status, DuplicateReview.Status.PENDING)
        blank = make_candidate(self.hr, email="", phone="", name="Blank A")
        other_blank = make_candidate(self.hr, email="", phone="", name="Blank B")
        queue_identity_duplicate_reviews(other_blank)
        self.assertFalse(DuplicateReview.objects.filter(candidate=other_blank, matched_candidate=blank).exists())
        review.decide(self.sales, approved=True, notes="Same person, keep both rows")
        review.refresh_from_db()
        self.assertEqual(review.status, DuplicateReview.Status.APPROVED)
        self.assertTrue(Candidate.objects.filter(pk=first.pk).exists())
        self.assertTrue(Candidate.objects.filter(pk=second.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="duplicate_review_approved", entity_id=str(review.pk)).exists())
        self.assertFalse(AuditLog.objects.get(entity_id=str(review.pk)).details["records_merged"])

    def test_user_without_review_permission_cannot_decide(self):
        first = make_candidate(self.hr, email="perm@example.com", phone="9333333333")
        second = make_candidate(self.hr, email="perm@example.com", phone="9444444444", name="Other")
        queue_identity_duplicate_reviews(second)
        review = DuplicateReview.objects.get(candidate=second)
        self.sales.groups.clear()
        self.sales.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            review.decide(self.sales, approved=True)
