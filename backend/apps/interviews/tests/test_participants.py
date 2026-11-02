from django.utils import timezone

from apps.applications.models import Application
from apps.interviews.models import Interview
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class InterviewParticipantApiTests(SynfoAPITestCase):
    def test_participants_follow_interview_permission(self):
        candidate = make_candidate(self.hr, email="panel@example.com", phone="9550000001")
        job = make_job(make_client(self.sales, "Panel Co"), self.sales, "Panel JD")
        application = Application.objects.create(candidate=candidate, job=job, recruiter=self.hr)
        interview = Interview.objects.create(
            application=application,
            round_name="Panel",
            interview_date=timezone.now(),
            feedback="PANEL-FEEDBACK",
            created_by=self.hr,
        )
        self.as_user(self.sales)
        self.assertEqual(self.client.get("/api/v1/interview-participants/").status_code, 403)
        self.as_user(self.hr)
        created = self.client.post(
            "/api/v1/interview-participants/",
            {"interview": str(interview.id), "user": str(self.hr.id), "role": "Recruiter"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        empty = self.client.post(
            "/api/v1/interview-participants/",
            {"interview": str(interview.id), "role": "Observer"},
            format="json",
        )
        self.assertEqual(empty.status_code, 400, empty.data)
        named = self.client.post(
            "/api/v1/interview-participants/",
            {"interview": str(interview.id), "name": "Client interviewer", "role": "Client"},
            format="json",
        )
        self.assertEqual(named.status_code, 201, named.data)
        duplicate = self.client.post(
            "/api/v1/interview-participants/",
            {"interview": str(interview.id), "user": str(self.hr.id), "role": "Again"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)
        listed = self.client.get("/api/v1/interview-participants/")
        self.assertEqual(listed.status_code, 200)
        names = {row["name"] or str(row["user"]) for row in listed.data["results"]}
        self.assertIn("Client interviewer", names)
        self.assertIn(str(self.hr.id), names)
        detail = self.client.get(f"/api/v1/interviews/{interview.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.data["participants"]), 2)
        self.assertIn("PANEL-FEEDBACK", detail.data["feedback"])
