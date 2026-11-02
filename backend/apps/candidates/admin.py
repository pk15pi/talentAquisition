from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
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
from apps.candidates.models import NON_CONSENT_BASES
from apps.matching.models import CandidateSkill
from apps.organizations.models import SystemConfiguration

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


class CandidateAdminForm(forms.ModelForm):
    """Creating a profile requires consent evidence or a written non-consent basis.

    The admin does not invent a consent time. Consent confirmation records the
    time of that confirmation. Another basis is stored on CandidateConsent and
    leaves consent_recorded_at empty.
    """

    processing_basis = forms.ChoiceField(
        choices=(("consent", "Consent"),) + tuple((basis, basis.replace("_", " ").title()) for basis in NON_CONSENT_BASES),
        initial="consent",
        required=False,
    )
    consent_confirmed = forms.BooleanField(
        required=False,
        label="Consent confirmed",
        help_text="Check this only after the candidate has agreed to the privacy notice version. The stored time is the time of this confirmation.",
    )
    basis_documentation = forms.CharField(
        required=False,
        widget=forms.Textarea,
        label="Basis documentation",
        help_text="Required for a basis other than consent. Record the source and why this profile may be stored. This is not a consent timestamp.",
    )

    class Meta:
        model = Candidate
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            for name in ("processing_basis", "consent_confirmed", "basis_documentation"):
                self.fields.pop(name, None)

    def clean(self):
        cleaned = super().clean()
        if not self.instance._state.adding:
            return cleaned
        basis = cleaned.get("processing_basis") or "consent"
        version = (cleaned.get("privacy_notice_version") or "").strip()
        if not version:
            self.add_error("privacy_notice_version", "Record the privacy notice version.")
        config = SystemConfiguration.objects.first()
        if config and config.privacy_notice_version and version and version != config.privacy_notice_version:
            self.add_error("privacy_notice_version", "Consent must match the current privacy notice version.")
        if basis == "consent":
            if not cleaned.get("consent_confirmed"):
                self.add_error(
                    "consent_confirmed",
                    "Confirm that the candidate consented, or choose a documented processing basis.",
                )
        else:
            note = (cleaned.get("basis_documentation") or "").strip()
            if len(note) < 10:
                self.add_error("basis_documentation", "Document the processing basis before storing this profile.")
            if cleaned.get("consent_confirmed"):
                self.add_error("consent_confirmed", "Do not mark consent when the basis is not consent.")
        cleaned["processing_basis"] = basis
        cleaned["privacy_notice_version"] = version
        return cleaned


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
        "consent_withdrawn_at",
        "merged_into",
        "merged_at",
        "created_at",
        "updated_at",
    )
    inlines = (CandidateSkillInline, ResumeInline, CandidateNoteInline, CandidateConsentInline, DuplicateReviewInline)
    form = CandidateAdminForm
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
        "merged_into",
        "merged_at",
        "is_active",
        "created_at",
        "updated_at",
    )
    actions = ("withdraw_recorded_consent",)

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj is None:
            extras = ["processing_basis", "consent_confirmed", "basis_documentation"]
            if "privacy_notice_version" in fields:
                index = fields.index("privacy_notice_version")
                for offset, name in enumerate(extras):
                    fields.insert(index + offset, name)
            else:
                fields.extend(extras)
        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.extend(["consent_withdrawn_at", "merged_into", "merged_at"])
        if obj is not None:
            readonly.extend(["consent_recorded_at", "privacy_notice_version"])
        return tuple(dict.fromkeys(readonly))

    @admin.action(description="Withdraw recorded consent without deleting the profile", permissions=["change"])
    def withdraw_recorded_consent(self, request, queryset):
        from apps.candidates.consent import withdraw_candidate_consent

        done = 0
        for candidate in queryset:
            try:
                withdraw_candidate_consent(candidate, request.user)
                done += 1
            except ValidationError as exc:
                message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                self.message_user(request, f"{candidate}: {message}", level=messages.WARNING)
        self.message_user(request, f"Withdrew consent on {done} profile(s). Profiles were not deleted.")

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
                    "merged_into",
                    "merged_at",
                }
            )
        return tuple(excluded) or None

    def get_fieldsets(self, request, obj=None):
        return strip_fieldsets(super().get_fieldsets(request, obj), set(self.get_exclude(request, obj) or ()))

    def save_model(self, request, obj, form, change):
        creating = not change
        basis = None
        documentation = ""
        if creating:
            if form is None or not getattr(form, "cleaned_data", None):
                raise ValidationError(
                    "Admin creation requires an explicit consent confirmation or a documented processing basis."
                )
            basis = form.cleaned_data.get("processing_basis") or "consent"
            documentation = (form.cleaned_data.get("basis_documentation") or "").strip()
            if basis == "consent":
                if not form.cleaned_data.get("consent_confirmed"):
                    raise ValidationError("Consent was not confirmed.")
                obj.consent_recorded_at = timezone.now()
            else:
                obj.consent_recorded_at = None
                obj._documented_processing_basis = basis
            if not obj.sourced_by_id:
                obj.sourced_by = request.user
        super().save_model(request, obj, form, change)
        if creating:
            CandidateConsent.objects.create(
                candidate=obj,
                purpose=documentation or "recruitment",
                source="admin",
                processing_basis=basis,
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
