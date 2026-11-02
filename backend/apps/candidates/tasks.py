from celery import shared_task
from django.core.files.storage import default_storage

from apps.audit.services import record_audit

from .models import Resume


def note_resume_parse_failure(resume, *, final):
    """Mark a parse as failed. The final attempt is written to the audit log.

    There is no notification recipient in the product rules, so the audit row
    is the operator record. The candidate screen shows parsing_status as well.
    """
    resume.parsing_status = "FAILED"
    resume.save(update_fields=["parsing_status"])
    if not final:
        return
    record_audit(
        user=resume.uploaded_by,
        action="resume_parse_failed",
        entity_type="candidates.Resume",
        entity_id=resume.pk,
        details={
            "candidate_id": str(resume.candidate_id),
            "original_filename": resume.original_filename,
            "retries_exhausted": True,
        },
    )


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def parse_resume(self, resume_id):
    resume = Resume.objects.get(pk=resume_id)
    resume.parsing_status = "PROCESSING"
    resume.save(update_fields=["parsing_status"])
    try:
        with default_storage.open(resume.file.name, "rb") as handle:
            raw = handle.read()
        name = resume.original_filename.lower()
        if name.endswith(".pdf"):
            import io

            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith(".docx"):
            import io

            from docx import Document

            document = Document(io.BytesIO(raw))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            raise ValueError("Unsupported resume format")
        resume.parsed_text = text[:200000]
        resume.parsing_status = "COMPLETED"
        resume.save(update_fields=["parsed_text", "parsing_status"])
    except Exception as exc:
        final = self.request.retries >= self.max_retries
        note_resume_parse_failure(resume, final=final)
        if final:
            raise
        raise self.retry(exc=exc)
