"""Fields the Phase 5 screens need and that the previous API did not return.

Permissions on ``/users/me/`` let the shell hide controls. They are not the
authorization check. Child-list filters keep a client, job, or candidate page
on the rows that belong to that record.
"""

from apps.candidates.models import CandidateNote
from apps.clients.models import ClientActivity
from apps.matching.models import JobSkill, Skill
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class CurrentUserContractTests(SynfoAPITestCase):
    def test_hr_me_exposes_permissions_and_hides_finance(self):
        self.as_user(self.hr)
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "hr")
        self.assertFalse(response.data["is_superuser"])
        self.assertIn("jobs.run_match", response.data["permissions"])
        self.assertIn("placements.view_placement", response.data["permissions"])
        self.assertNotIn("billing.view_invoice", response.data["permissions"])
        self.assertNotIn("placements.view_placement_financials", response.data["permissions"])
        self.assertNotIn("reports.view_financial_report", response.data["permissions"])
        self.assertTrue(response.data["can_be_assigned_recruiter"])
        self.assertFalse(response.data["can_own_client"])
        self.assertNotIn("permissions", self.client.get("/api/v1/users/").data["results"][0])

    def test_sales_me_cannot_run_match_and_can_own_clients(self):
        self.as_user(self.sales)
        response = self.client.get("/api/v1/users/me/")
        self.assertNotIn("jobs.run_match", response.data["permissions"])
        self.assertNotIn("billing.view_invoice", response.data["permissions"])
        self.assertTrue(response.data["can_own_client"])
        self.assertFalse(response.data["can_be_assigned_recruiter"])

    def test_superuser_me_is_flagged_even_after_groups_are_cleared(self):
        self.root.groups.clear()
        self.root.user_permissions.clear()
        self.as_user(self.root)
        response = self.client.get("/api/v1/users/me/")
        self.assertTrue(response.data["is_superuser"])
        self.assertIn("billing.view_invoice", response.data["permissions"])


class ChildListFilterTests(SynfoAPITestCase):
    def test_job_skills_activities_and_notes_filter_by_parent(self):
        client = make_client(self.sales, "Filter Co")
        other_client = make_client(self.sales, "Other Co")
        job = make_job(client, self.sales, "Filter JD")
        other_job = make_job(client, self.sales, "Other JD")
        skill = Skill.objects.create(name="Python", normalized_name="python-ui-contract")
        JobSkill.objects.create(job=job, skill=skill, is_mandatory=True, weight=5)
        JobSkill.objects.create(job=other_job, skill=skill, weight=1)
        ClientActivity.objects.create(client=client, user=self.hr, activity_type="NOTE", subject="Hello")
        ClientActivity.objects.create(client=other_client, user=self.hr, activity_type="NOTE", subject="Elsewhere")
        candidate = make_candidate(self.hr, email="filter@example.com", phone="9001112222", name="Filter Candidate")
        other = make_candidate(self.hr, email="other-filter@example.com", phone="9001112223", name="Other Candidate")
        CandidateNote.objects.create(candidate=candidate, user=self.hr, note="Keep")
        CandidateNote.objects.create(candidate=other, user=self.hr, note="Drop")

        self.as_user(self.hr)
        skills = self.client.get("/api/v1/job-skills/", {"job": str(job.id)})
        self.assertEqual(skills.status_code, 200, skills.data)
        self.assertEqual(len(skills.data["results"]), 1)
        self.assertEqual(skills.data["results"][0]["skill_name"], "Python")
        self.assertTrue(skills.data["results"][0]["is_mandatory"])
        bad = self.client.get("/api/v1/job-skills/", {"job": "not-a-uuid"})
        self.assertEqual(bad.status_code, 200)
        self.assertEqual(bad.data["results"], [])

        activities = self.client.get("/api/v1/client-activities/", {"client": str(client.id)})
        self.assertEqual([row["subject"] for row in activities.data["results"]], ["Hello"])
        self.assertEqual(activities.data["results"][0]["user_name"], "hr")

        notes = self.client.get("/api/v1/candidate-notes/", {"candidate": str(candidate.id)})
        self.assertEqual([row["note"] for row in notes.data["results"]], ["Keep"])
