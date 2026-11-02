from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.candidates.models import Resume
from apps.matching.models import MatchRun
from apps.testkit import SynfoAPITestCase, make_candidate, make_client, make_job


SECRET_TEXT = "SECRET-PARSED-RESUME-TEXT"
SECRET_HASH = "abc123secretfilehash"
SECRET_CTC = "999999.00"


class ResumePrivacyTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.candidate = make_candidate(self.hr, email="private@example.com", phone="9777777777", name="Private Person")
        self.candidate.current_ctc = Decimal(SECRET_CTC)
        self.candidate.expected_ctc = Decimal("1200000.00")
        self.candidate.save()
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=SimpleUploadedFile("secret-resume.pdf", b"%PDF-1.4 secret"),
            original_filename="secret-resume.pdf",
            file_hash=SECRET_HASH,
            parsed_text=SECRET_TEXT,
            parsing_status="COMPLETED",
            version=1,
            is_primary=True,
            uploaded_by=self.hr,
        )

    def _assert_no_resume_secrets(self, payload):
        blob = str(payload)
        self.assertNotIn(SECRET_TEXT, blob)
        self.assertNotIn(SECRET_HASH, blob)
        self.assertNotIn("parsed_text", blob)
        self.assertNotIn("file_hash", blob)
        self.assertNotIn("/media/", blob)
        self.assertNotIn("resumes/", blob)

    def test_sales_cannot_read_candidates(self):
        self.as_user(self.sales)
        response = self.client.get("/api/v1/candidates/")
        self.assertEqual(response.status_code, 403)
        detail = self.client.get(f"/api/v1/candidates/{self.candidate.id}/")
        self.assertEqual(detail.status_code, 403)

    def test_hr_candidate_payload_omits_resume_content_and_compensation(self):
        self.as_user(self.hr)
        response = self.client.get(f"/api/v1/candidates/{self.candidate.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self._assert_no_resume_secrets(response.data)
        self.assertNotIn("current_ctc", response.data)
        self.assertNotIn("expected_ctc", response.data)
        self.assertEqual(response.data["resumes"][0]["original_filename"], "secret-resume.pdf")
        self.assertNotIn("file", response.data["resumes"][0])

    def test_management_can_see_compensation_but_not_resume_content(self):
        self.as_user(self.management)
        response = self.client.get(f"/api/v1/candidates/{self.candidate.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self._assert_no_resume_secrets(response.data)
        self.assertEqual(response.data["current_ctc"], SECRET_CTC)

    def test_upload_response_does_not_return_storage_or_parsed_text(self):
        self.as_user(self.hr)
        upload = SimpleUploadedFile("other.docx", b"PK\x03\x04 not-a-real-docx")
        with patch("apps.candidates.tasks.parse_resume.delay"):
            response = self.client.post(
                f"/api/v1/candidates/{self.candidate.id}/upload-resume/",
                {"file": upload},
                format="multipart",
            )
        self.assertEqual(response.status_code, 201, response.data)
        self._assert_no_resume_secrets(response.data)
        self.assertEqual(response.data["original_filename"], "other.docx")

    def test_media_url_is_not_a_download(self):
        response = self.client.get(self.resume.file.url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(SECRET_TEXT.encode(), response.content)

    def test_staff_without_resume_permission_cannot_see_content_in_admin(self):
        self.hr.is_staff = True
        self.hr.save()
        admin_client = Client()
        admin_client.force_login(self.hr)
        resume_page = admin_client.get(f"/admin/candidates/resume/{self.resume.id}/change/")
        self.assertEqual(resume_page.status_code, 200)
        self.assertNotIn(SECRET_TEXT.encode(), resume_page.content)
        self.assertNotIn(SECRET_HASH.encode(), resume_page.content)
        self.assertNotIn(b"parsed_text", resume_page.content)
        self.assertNotIn(b"type=\"file\"", resume_page.content)
        candidate_page = admin_client.get(f"/admin/candidates/candidate/{self.candidate.id}/change/")
        self.assertEqual(candidate_page.status_code, 200)
        self.assertNotIn(b"current_ctc", candidate_page.content)
        self.assertNotIn(SECRET_CTC.encode(), candidate_page.content)

    def test_match_runs_without_leaking_resume_data(self):
        job = make_job(make_client(self.sales, "Match Co"), self.sales, "Match JD")
        self.lead.groups  # touch
        before = MatchRun.objects.count()
        self.as_user(self.hr)
        # HR is not assigned, so the job is outside their queryset.
        hidden = self.client.post(f"/api/v1/jobs/{job.id}/match/")
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(MatchRun.objects.count(), before)
        self.as_user(self.lead)
        matched = self.client.post(f"/api/v1/jobs/{job.id}/match/")
        self.assertEqual(matched.status_code, 200, matched.data)
        self.assertNotEqual(matched.data.get("code"), "matching_unavailable")
        self._assert_no_resume_secrets(matched.data)
        self.assertEqual(MatchRun.objects.filter(job=job, completed_at__isnull=False).count(), 1)
        self.assertEqual(matched.data["candidates_processed"], 1)
