from django.core.files.uploadedfile import SimpleUploadedFile

from apps.applications.models import Application
from apps.candidates.models import Resume
from apps.recruitment.models import Submission
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


class SubmissionApiTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.candidate = make_candidate(self.hr, email="submit@example.com", phone="9660000001", name="Submit Person")
        self.other = make_candidate(self.hr, email="other-submit@example.com", phone="9660000002", name="Other Person")
        self.job = make_job(make_client(self.sales, "Submit Co"), self.sales, "Submit JD")
        self.application = Application.objects.create(candidate=self.candidate, job=self.job, recruiter=self.hr)
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=SimpleUploadedFile("submit.pdf", b"%PDF submit"),
            original_filename="submit.pdf",
            version=1,
            is_primary=True,
            uploaded_by=self.hr,
        )
        self.other_resume = Resume.objects.create(
            candidate=self.other,
            file=SimpleUploadedFile("other.pdf", b"%PDF other"),
            original_filename="other.pdf",
            version=1,
            is_primary=True,
            uploaded_by=self.hr,
        )

    def test_hr_can_submit_and_move_status_without_sales_access(self):
        self.as_user(self.sales)
        self.assertEqual(self.client.get("/api/v1/submissions/").status_code, 403)
        self.as_user(self.hr)
        created = self.client.post(
            "/api/v1/submissions/",
            {
                "application": str(self.application.id),
                "resume": str(self.resume.id),
                "response_status": "SHORTLISTED",
                "submitted_by": str(self.sales.id),
                "client_feedback": "Sent to the hiring manager",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["response_status"], "PENDING")
        self.assertEqual(str(created.data["submitted_by"]), str(self.hr.id))
        self.assertEqual(len(str(created.data["id"])), 36)
        wrong_resume = self.client.post(
            "/api/v1/submissions/",
            {"application": str(self.application.id), "resume": str(self.other_resume.id)},
            format="json",
        )
        self.assertEqual(wrong_resume.status_code, 400, wrong_resume.data)
        illegal = self.client.patch(
            f"/api/v1/submissions/{created.data['id']}/",
            {"response_status": "SHORTLISTED"},
            format="json",
        )
        self.assertEqual(illegal.status_code, 400, illegal.data)
        self.assertEqual(Submission.objects.get(pk=created.data["id"]).response_status, "PENDING")
        acknowledged = self.client.patch(
            f"/api/v1/submissions/{created.data['id']}/",
            {"response_status": "ACKNOWLEDGED"},
            format="json",
        )
        self.assertEqual(acknowledged.status_code, 200, acknowledged.data)
        self.assertEqual(acknowledged.data["response_status"], "ACKNOWLEDGED")
        self.assertEqual(self.client.delete(f"/api/v1/submissions/{created.data['id']}/").status_code, 403)
        self.assertTrue(Submission.objects.filter(pk=created.data["id"]).exists())
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "IDENTIFIED")
