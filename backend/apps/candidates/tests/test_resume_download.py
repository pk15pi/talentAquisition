import time
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.candidates.downloads import DOWNLOAD_MAX_AGE_SECONDS, make_download_token
from apps.candidates.models import Resume
from apps.testkit import SynfoAPITestCase, make_candidate

FILE_BYTES = b"%PDF-1.4 authorized-bytes"
PARSED = "DOWNLOAD-PARSED-SECRET"
FILE_HASH = "download-hash-secret"


class ResumeDownloadTests(SynfoAPITestCase):
    def setUp(self):
        super().setUp()
        self.candidate = make_candidate(self.hr, email="download@example.com", phone="9888888881", name="Download Person")
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=SimpleUploadedFile("authorized.pdf", FILE_BYTES),
            original_filename="authorized.pdf",
            file_hash=FILE_HASH,
            parsed_text=PARSED,
            parsing_status="COMPLETED",
            is_primary=True,
            uploaded_by=self.hr,
        )

    def test_signed_download_requires_resume_content_permission_and_hides_media(self):
        self.as_user(self.hr)
        hr_link = self.client.post(f"/api/v1/resumes/{self.resume.id}/download/")
        self.assertEqual(hr_link.status_code, 403)
        self.as_user(self.management)
        management_link = self.client.post(f"/api/v1/resumes/{self.resume.id}/download/")
        self.assertEqual(management_link.status_code, 403)
        self.client.force_authenticate(user=None)
        anonymous = self.client.post(f"/api/v1/resumes/{self.resume.id}/download/")
        self.assertEqual(anonymous.status_code, 401)

        self.as_user(self.admin)
        link = self.client.post(f"/api/v1/resumes/{self.resume.id}/download/")
        self.assertEqual(link.status_code, 200, link.data)
        self.assertNotIn(PARSED, str(link.data))
        self.assertNotIn(FILE_HASH, str(link.data))
        self.assertNotIn("/media/", link.data["download_path"])
        self.assertTrue(link.data["download_path"].startswith("/api/v1/resume-downloads/?"))

        self.client.force_authenticate(user=None)
        downloaded = self.client.get(link.data["download_path"])
        body = b"".join(downloaded.streaming_content)
        self.assertEqual(downloaded.status_code, 200, body[:200])
        self.assertIn(FILE_BYTES, body)
        self.assertNotIn(PARSED.encode(), body)
        public = self.client.get(self.resume.file.url)
        self.assertEqual(public.status_code, 404)

        tampered = self.client.get(link.data["download_path"] + "tampered")
        self.assertEqual(tampered.status_code, 403)

        self.admin.groups.clear()
        self.admin.user_permissions.clear()
        revoked = self.client.get(link.data["download_path"])
        self.assertEqual(revoked.status_code, 403)

    def test_expired_token_is_rejected(self):
        with patch("django.core.signing.time.time", return_value=time.time() - DOWNLOAD_MAX_AGE_SECONDS - 10):
            token = make_download_token(self.admin, self.resume)
        response = self.client.get("/api/v1/resume-downloads/", {"token": token})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "invalid_download_link")

    def test_direct_permission_grant_can_mint_a_link(self):
        self.sales.groups.clear()
        self.sales.user_permissions.clear()
        permission = Permission.objects.get(content_type__app_label="candidates", codename="view_resume_content")
        self.sales.user_permissions.add(permission)
        self.sales = type(self.sales).objects.get(pk=self.sales.pk)
        self.as_user(self.sales)
        link = self.client.post(f"/api/v1/resumes/{self.resume.id}/download/")
        self.assertEqual(link.status_code, 200, link.data)
