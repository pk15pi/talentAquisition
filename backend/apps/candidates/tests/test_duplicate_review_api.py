from decimal import Decimal

from apps.audit.models import AuditLog
from apps.candidates.models import Candidate, DuplicateReview
from apps.candidates.reviews import queue_identity_duplicate_reviews
from apps.testkit import SynfoAPITestCase, make_candidate


class DuplicateReviewApiTests(SynfoAPITestCase):
    def test_decide_approves_without_merging_or_deleting(self):
        first = make_candidate(self.hr, email="api-dup@example.com", phone="9770000001", name="Kept First")
        first.current_ctc = Decimal("555000.00")
        first.save()
        second = make_candidate(self.hr, email="api-dup@example.com", phone="9770000002", name="Kept Second")
        queue_identity_duplicate_reviews(second)
        review = DuplicateReview.objects.get(candidate=second, matched_candidate=first)
        self.sales.groups.clear()
        self.sales.user_permissions.clear()
        self.sales = type(self.sales).objects.get(pk=self.sales.pk)
        self.as_user(self.sales)
        self.assertEqual(self.client.get("/api/v1/duplicate-reviews/").status_code, 403)
        self.as_user(self.hr)
        listed = self.client.get("/api/v1/duplicate-reviews/")
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertNotIn("555000.00", str(listed.data))
        self.assertNotIn("current_ctc", str(listed.data))
        decided = self.client.post(
            f"/api/v1/duplicate-reviews/{review.id}/decide/",
            {"approved": True, "notes": "Same person, keep both rows"},
            format="json",
        )
        self.assertEqual(decided.status_code, 200, decided.data)
        self.assertEqual(decided.data["status"], "APPROVED")
        self.assertEqual(Candidate.objects.get(pk=first.pk).full_name, "Kept First")
        self.assertEqual(Candidate.objects.get(pk=second.pk).full_name, "Kept Second")
        self.assertEqual(Candidate.objects.filter(pk__in=[first.pk, second.pk]).count(), 2)
        log = AuditLog.objects.get(action="duplicate_review_approved", entity_id=str(review.pk))
        self.assertFalse(log.details["records_merged"])
        again = self.client.post(
            f"/api/v1/duplicate-reviews/{review.id}/decide/",
            {"approved": False},
            format="json",
        )
        self.assertEqual(again.status_code, 400, again.data)
        review.refresh_from_db()
        self.assertEqual(review.status, DuplicateReview.Status.APPROVED)
