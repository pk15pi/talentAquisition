from celery import shared_task
from django.core.files.storage import default_storage
from .models import Resume
@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def parse_resume(self, resume_id):
    resume=Resume.objects.get(pk=resume_id)
    resume.parsing_status="PROCESSING"; resume.save(update_fields=["parsing_status"])
    try:
        with default_storage.open(resume.file.name,"rb") as handle:
            raw=handle.read()
        name=resume.original_filename.lower()
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            import io
            reader=PdfReader(io.BytesIO(raw)); text="\n".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith(".docx"):
            from docx import Document
            import io
            document=Document(io.BytesIO(raw)); text="\n".join(p.text for p in document.paragraphs)
        else:
            raise ValueError("Unsupported resume format")
        resume.parsed_text=text[:200000]; resume.parsing_status="COMPLETED"
        resume.save(update_fields=["parsed_text","parsing_status"])
    except Exception as exc:
        resume.parsing_status="FAILED"; resume.save(update_fields=["parsing_status"])
        raise self.retry(exc=exc)
