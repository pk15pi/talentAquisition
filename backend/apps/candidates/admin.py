from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.admin_access import (
    HistoryInlineMixin,
    ParentInlineMixin,
    ReadOnlyModelAdmin,
    SensitiveFieldsMixin,
    SensitiveModelAdmin,
    perm,
    strip_fieldsets,
)
from apps.matching.models import CandidateSkill

from .models import Candidate, CandidateConsent, CandidateNote, DuplicateReview, Resume
from .reviews import queue_identity_duplicate_reviews

COMPENSATION_FIELDS = ("current_ctc", "expected_ctc")
RESUME_CONTENT_FIELDS = ("file", "parsed_text", "file_hash")


class CandidateNoteInline(ParentInlineMixin, admin.TabularInline):
    model = CandidateNote
    extra = 0
    parent_view_permission = "candidates.view_candidate"
    edit_permission = "candidates.add_candidatenote"
    fields = ("note", "user", "created_at")
    readonly_fields = ("user", "created_at")
    ordering = ("-created_at",)

    def has_change_permission(self, request, obj=None):
        return False


class ResumeInline(SensitiveFieldsMixin, ParentInlineMixin, admin.TabularInline):
    model = Resume
    extra = 0
    parent_view_permission = "candidates.view_resume"
    edit_permission = "candidates.change_resume"
    sensitive_field_rules = (("candidates.view_resume_content", RESUME_CONTENT_FIELDS, "candidates.change_resume"),)
    fields = (
        "original_filename",
        "parsing_status",
        "version",
        "is_primary",
        "uploaded_by",
        "uploaded_at",
        "file",
        "parsed_text",
        "file_hash",
    )
    readonly_fields = ("uploaded_by", "uploaded_at", "version")
    show_change_link = True
    ordering = ("-version",)

    def has_add_permission(self, request, obj=None):
        return super().has_add_permission(request, obj) and perm(request.user, "candidates.view_resume_content")


class CandidateConsentInline(HistoryInlineMixin, admin.TabularInline):
    model = CandidateConsent
    parent_view_permission = "candidates.view_candidate"
    fields = ("purpose", "source", "processing_basis", "privacy_notice_version", "recorded_by", "recorded_at", "withdrawn_at")
    readonly_fields = fields
    ordering = ("-recorded_at",)
    verbose_name_plural = "Consent history"


class CandidateSkillInline(ParentInlineMixin, admin.TabularInline):
    model = CandidateSkill
    extra = 0
    parent_view_permission = "matching.view_candidateskill"
    edit_permission = "matching.change_candidateskill"
    allow_delete = True
    autocomplete_fields = ("skill",)
    fields = ("skill", "experience_months")


class DuplicateReviewInline(HistoryInlineMixin, admin.TabularInline):
    model = DuplicateReview
    fk_name = "candidate"
    parent_view_permission = "candidates.view_candidate"
    fields = ("matched_candidate", "match_type", "status", "reviewed_by", "reviewed_at", "created_at")
    readonly_fields = fields
    ordering = ("-created_at",)
    verbose_name_plural = "Duplicate reviews"
    show_change_link = True


@admin.register(Candidate)
class CandidateAdmin(SensitiveModelAdmin):
    sensitive_field_rules = (("candidates.view_candidate_compensation", COMPENSATION_FIELDS),)
    list_display = ("candidate_code", "full_name", "email", "phone", "source", "is_active", "current_ctc", "created_at")
    list_display_links = ("candidate_code", "full_name")
    list_filter = ("source", "is_active")
    search_fields = ("candidate_code", "full_name", "email", "phone", "current_company", "location")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("sourced_by",)
    readonly_fields = (
        "candidate_code",
        "normalized_email",
        "normalized_phone",
        "sourced_by",
        "created_at",
        "updated_at",
    )
    inlines = (CandidateSkillInline, ResumeInline, CandidateNoteInline, CandidateConsentInline, DuplicateReviewInline)
    fields = (
        "candidate_code",
        "full_name",
        "email",
        "phone",
        "normalized_email",
        "normalized_phone",
        "current_company",
        "total_experience",
        "current_ctc",
        "expected_ctc",
        "location",
        "notice_period_days",
        "source",
        "sourced_by",
        "consent_recorded_at",
        "privacy_notice_version",
        "consent_withdrawn_at",
        "is_active",
        "created_at",
        "updated_at",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly.extend(["consent_recorded_at", "privacy_notice_version"])
        return tuple(dict.fromkeys(readonly))

    def get_exclude(self, request, obj=None):
        excluded = set(super().get_exclude(request, obj) or ())
        if obj is None:
            excluded.update(
                {
                    "consent_recorded_at",
                    "consent_withdrawn_at",
                    "candidate_code",
                    "sourced_by",
                    "normalized_email",
                    "normalized_phone",
                }
            )
        return tuple(excluded) or None

    def get_fieldsets(self, request, obj=None):
        return strip_fieldsets(super().get_fieldsets(request, obj), set(self.get_exclude(request, obj) or ()))

    def save_model(self, request, obj, form, change):
        creating = not change
        if creating:
            if not obj.sourced_by_id:
                obj.sourced_by = request.user
            if not obj.consent_recorded_at:
                obj.consent_recorded_at = timezone.now()
        super().save_model(request, obj, form, change)
        if creating:
            CandidateConsent.objects.create(
                candidate=obj,
                purpose="recruitment",
                source="admin",
                processing_basis="consent",
                privacy_notice_version=obj.privacy_notice_version,
                recorded_by=request.user,
            )
            queue_identity_duplicate_reviews(obj)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if isinstance(obj, CandidateNote) and not obj.user_id:
                obj.user = request.user
            if isinstance(obj, Resume):
                if not obj.uploaded_by_id:
                    obj.uploaded_by = request.user
                if obj._state.adding:
                    current = obj.candidate.resumes.order_by("-version").values_list("version", flat=True).first() or 0
                    obj.version = current + 1
            obj.save()
        formset.save_m2m()


@admin.register(Resume)
class ResumeAdmin(SensitiveModelAdmin):
    sensitive_field_rules = (("candidates.view_resume_content", RESUME_CONTENT_FIELDS, "candidates.change_resume"),)
    list_display = ("candidate", "original_filename", "parsing_status", "version", "is_primary", "uploaded_at")
    list_filter = ("parsing_status", "is_primary")
    search_fields = ("original_filename", "candidate__full_name", "candidate__candidate_code")
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)
    list_select_related = ("candidate", "uploaded_by")
    autocomplete_fields = ("candidate",)
    readonly_fields = ("uploaded_by", "uploaded_at")
    fields = (
        "candidate",
        "original_filename",
        "parsing_status",
        "version",
        "is_primary",
        "uploaded_by",
        "uploaded_at",
        "file",
        "parsed_text",
        "file_hash",
    )

    def has_add_permission(self, request):
        return super().has_add_permission(request) and perm(request.user, "candidates.view_resume_content")

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        if not change:
            current = Resume.objects.filter(candidate=obj.candidate).order_by("-version").values_list("version", flat=True).first() or 0
            obj.version = current + 1
        super().save_model(request, obj, form, change)


@admin.register(CandidateNote)
class CandidateNoteAdmin(ReadOnlyModelAdmin):
    list_display = ("candidate", "user", "created_at")
    search_fields = ("note", "candidate__full_name", "candidate__candidate_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("candidate", "user")
    autocomplete_fields = ("candidate",)
    readonly_fields = ("user", "created_at")

    def has_add_permission(self, request):
        return perm(request.user, "candidates.add_candidatenote")

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super(ReadOnlyModelAdmin, self).save_model(request, obj, form, change)


@admin.register(CandidateConsent)
class CandidateConsentAdmin(ReadOnlyModelAdmin):
    list_display = ("candidate", "purpose", "privacy_notice_version", "recorded_by", "recorded_at", "withdrawn_at")
    search_fields = ("candidate__full_name", "candidate__candidate_code", "purpose", "privacy_notice_version")
    date_hierarchy = "recorded_at"
    ordering = ("-recorded_at",)
    list_select_related = ("candidate", "recorded_by")


@admin.action(description="Approve selected reviews without merging profiles", permissions=["review_duplicate"])
def approve_duplicate_reviews(modeladmin, request, queryset):
    _decide_reviews(modeladmin, request, queryset, approved=True)


@admin.action(description="Reject selected reviews without merging profiles", permissions=["review_duplicate"])
def reject_duplicate_reviews(modeladmin, request, queryset):
    _decide_reviews(modeladmin, request, queryset, approved=False)


def _decide_reviews(modeladmin, request, queryset, approved):
    if not perm(request.user, "candidates.review_duplicate"):
        raise PermissionDenied("You do not have permission to decide duplicate reviews.")
    decided = 0
    for review in queryset.filter(status=DuplicateReview.Status.PENDING):
        review.decide(request.user, approved=approved, notes="Decided in admin")
        decided += 1
    verb = "Approved" if approved else "Rejected"
    modeladmin.message_user(request, f"{verb} {decided} duplicate review(s). No profiles were merged or deleted.")


@admin.register(DuplicateReview)
class DuplicateReviewAdmin(ReadOnlyModelAdmin):
    list_display = ("candidate", "matched_candidate", "match_type", "status", "reviewed_by", "created_at")
    list_filter = ("status", "match_type")
    search_fields = (
        "candidate__full_name",
        "candidate__candidate_code",
        "matched_candidate__full_name",
        "matched_candidate__candidate_code",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("candidate", "matched_candidate", "reviewed_by")
    actions = (approve_duplicate_reviews, reject_duplicate_reviews)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) or perm(request.user, "candidates.review_duplicate")

    def has_review_duplicate_permission(self, request):
        return perm(request.user, "candidates.review_duplicate")
