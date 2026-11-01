from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class GroupAccessMatrixTests(SynfoAPITestCase):
    """Creation and visibility for the five default groups. Permissions, not role strings, decide access."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.candidate = make_candidate(cls.hr, email="shared@example.com", phone="9666666661", name="Shared Pool")
        cls.owned = make_job(make_client(cls.sales, "Sales Client"), cls.sales, "Owned JD")
        cls.other = make_job(make_client(cls.sales_two, "Other Client"), cls.sales_two, "Other JD")

    def test_candidate_visibility_is_limited_to_groups_with_view_candidate(self):
        for user, allowed in (
            (self.sales, False),
            (self.hr, True),
            (self.lead, True),
            (self.management, True),
            (self.admin, True),
        ):
            self.as_user(user)
            response = self.client.get("/api/v1/candidates/")
            self.assertEqual(response.status_code, 200 if allowed else 403, user.username)

    def test_job_scope_and_assignment(self):
        self.as_user(self.sales)
        own = self.client.get(f"/api/v1/jobs/{self.owned.id}/")
        other = self.client.get(f"/api/v1/jobs/{self.other.id}/")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(other.status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/jobs/{self.owned.id}/assign/", {"recruiter_ids": [str(self.hr.id)]}, format="json").status_code, 403)

        self.as_user(self.hr)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{self.owned.id}/").status_code, 404)

        self.as_user(self.lead)
        assigned = self.client.post(
            f"/api/v1/jobs/{self.owned.id}/assign/",
            {"recruiter_ids": [str(self.hr.id)]},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200, assigned.data)
        self.as_user(self.hr)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{self.owned.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{self.other.id}/").status_code, 404)

        self.as_user(self.management)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{self.other.id}/").status_code, 200)
        self.as_user(self.admin)
        self.assertEqual(self.client.get(f"/api/v1/jobs/{self.other.id}/").status_code, 200)

    def test_interview_feedback_is_hidden_from_sales(self):
        from django.utils import timezone

        from apps.applications.models import Application
        from apps.interviews.models import Interview

        application = Application.objects.create(candidate=self.candidate, job=self.owned, recruiter=self.hr)
        Interview.objects.create(
            application=application,
            round_name="L1",
            interview_date=timezone.now(),
            feedback="CONFIDENTIAL-FEEDBACK",
            created_by=self.hr,
        )
        self.as_user(self.sales)
        self.assertEqual(self.client.get("/api/v1/interviews/").status_code, 403)
        self.as_user(self.hr)
        visible = self.client.get("/api/v1/interviews/")
        self.assertEqual(visible.status_code, 200)
        self.assertIn("CONFIDENTIAL-FEEDBACK", str(visible.data))
        self.as_user(self.management)
        self.assertEqual(self.client.get("/api/v1/interviews/").status_code, 200)
