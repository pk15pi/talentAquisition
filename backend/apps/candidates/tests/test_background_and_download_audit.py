from apps.audit.models import AuditLog
from apps.candidates.tasks import note_resume_parse_failure
from apps.testkit import SynfoAPITestCase, make_candidate


class BackgroundFailureAuditTests(SynfoAPITestCase):
    def test_final_parse_failure_is_audited_and_listed(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.candidates.models import Resume

        candidate = make_candidate(self.hr, email="parse@example.com", phone="9200000001", name="Parse")
        resume = Resume.objects.create(
            candidate=candidate,
            file=SimpleUploadedFile("bad.txt", b"not-a-resume"),
            original_filename="bad.txt",
            version=1,
            uploaded_by=self.hr,
        )
        note_resume_parse_failure(resume, final=False)
        self.assertFalse(AuditLog.objects.filter(action="resume_parse_failed").exists())
        note_resume_parse_failure(resume, final=True)
        resume.refresh_from_db()
        self.assertEqual(resume.parsing_status, "FAILED")
        self.as_user(self.admin)
        listing = self.client.get("/api/v1/audit-logs/", {"action": "resume_parse_failed"})
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["count"], 1)
        self.as_user(self.hr)
        denied = self.client.get("/api/v1/audit-logs/")
        self.assertEqual(denied.status_code, 403)

    def test_resume_download_writes_an_audit_row(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.candidates.models import Resume

        candidate = make_candidate(self.hr, email="audit-dl@example.com", phone="9200000002", name="Audit Download")
        resume = Resume.objects.create(
            candidate=candidate,
            file=SimpleUploadedFile("audit.pdf", b"%PDF-1.4 audit"),
            original_filename="audit.pdf",
            version=1,
            uploaded_by=self.hr,
        )
        self.as_user(self.admin)
        link = self.client.post(f"/api/v1/resumes/{resume.id}/download/")
        self.assertEqual(link.status_code, 200, link.data)
        self.client.force_authenticate(user=None)
        downloaded = self.client.get(link.data["download_path"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="resume_download_link", entity_id=str(resume.id)).exists())
        self.assertTrue(AuditLog.objects.filter(action="resume_downloaded", entity_id=str(resume.id), user=self.admin).exists())
