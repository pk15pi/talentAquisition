from django.contrib import admin

from .models import Candidate, CandidateConsent, CandidateNote, DuplicateReview, Resume

COMPENSATION_FIELDS = ("current_ctc", "expected_ctc")
RESUME_CONTENT_FIELDS = ("file", "parsed_text", "file_hash")


def _without(fields, hidden):
    return [field for field in fields if field not in hidden]


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.has_perm("candidates.view_candidate_compensation"):
            fields = _without(fields, COMPENSATION_FIELDS)
        return fields

    def get_exclude(self, request, obj=None):
        excluded = set(super().get_exclude(request, obj) or ())
        if not request.user.has_perm("candidates.view_candidate_compensation"):
            excluded.update(COMPENSATION_FIELDS)
        return tuple(excluded) or None


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.has_perm("candidates.view_resume_content"):
            fields = _without(fields, RESUME_CONTENT_FIELDS)
        return fields

    def get_exclude(self, request, obj=None):
        excluded = set(super().get_exclude(request, obj) or ())
        if not request.user.has_perm("candidates.view_resume_content"):
            excluded.update(RESUME_CONTENT_FIELDS)
        return tuple(excluded) or None


admin.site.register([CandidateNote, CandidateConsent, DuplicateReview])
