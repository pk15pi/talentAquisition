from django import forms
from django.contrib import admin

from apps.access import visible_applications
from apps.admin_access import HistoryInlineMixin, NoDeleteMixin, ParentInlineMixin, ReadOnlyModelAdmin
from apps.recruitment.models import Submission

from .models import Application, ApplicationHistory
from .services import allowed_status_transitions


class ApplicationAdminForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        new_status = cleaned.get("status")
        if self.instance.pk and new_status:
            old_status = Application.objects.filter(pk=self.instance.pk).values_list("status", flat=True).first()
            allowed = allowed_status_transitions(old_status) if old_status else set()
            if old_status and old_status != new_status and new_status not in allowed:
                allowed_text = ", ".join(sorted(allowed)) if allowed else "none"
                raise forms.ValidationError(
                    f"Cannot move an application from {old_status} to {new_status}. Allowed: {allowed_text}."
                )
        return cleaned


class ApplicationHistoryInline(HistoryInlineMixin, admin.TabularInline):
    model = ApplicationHistory
    parent_view_permission = "applications.view_application"
    fields = ("old_status", "new_status", "changed_by", "changed_at", "remarks")
    readonly_fields = fields
    ordering = ("-changed_at",)
    verbose_name_plural = "Status history"


class SubmissionInline(ParentInlineMixin, admin.TabularInline):
    model = Submission
    extra = 0
    parent_view_permission = "applications.view_application"
    edit_permission = "recruitment.change_submission"
    autocomplete_fields = ("submitted_by", "resume")
    fields = ("submitted_by", "resume", "submission_date", "response_status", "client_feedback")
    readonly_fields = ("submission_date",)


@admin.register(Application)
class ApplicationAdmin(NoDeleteMixin, admin.ModelAdmin):
    form = ApplicationAdminForm
    list_display = ("application_code", "candidate", "job", "recruiter", "status", "created_at")
    list_filter = ("status",)
    search_fields = (
        "application_code",
        "candidate__full_name",
        "candidate__candidate_code",
        "job__title",
        "job__job_code",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("candidate", "job", "recruiter")
    autocomplete_fields = ("candidate", "job")
    readonly_fields = ("application_code", "recruiter", "sourced_by", "created_at", "updated_at")
    inlines = (ApplicationHistoryInline, SubmissionInline)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=visible_applications(request.user).values("pk"))
            .select_related("candidate", "job", "recruiter", "sourced_by")
        )

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous = Application.objects.filter(pk=obj.pk).values("status", "recruiter_id", "sourced_by_id").first()
            if previous:
                previous_status = previous["status"]
                obj.recruiter_id = previous["recruiter_id"]
                obj.sourced_by_id = previous["sourced_by_id"]
        else:
            if not obj.recruiter_id:
                obj.recruiter = request.user
            if not obj.sourced_by_id:
                obj.sourced_by = request.user
        super().save_model(request, obj, form, change)
        if not change or previous_status != obj.status:
            ApplicationHistory.objects.create(
                application=obj,
                old_status="" if not change else (previous_status or ""),
                new_status=obj.status,
                changed_by=request.user,
                remarks="Application created" if not change else "Status changed in admin",
            )


@admin.register(ApplicationHistory)
class ApplicationHistoryAdmin(ReadOnlyModelAdmin):
    list_display = ("application", "old_status", "new_status", "changed_by", "changed_at")
    search_fields = ("application__application_code", "old_status", "new_status", "remarks")
    date_hierarchy = "changed_at"
    ordering = ("-changed_at",)
    list_select_related = ("application", "changed_by")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(application__in=visible_applications(request.user))
            .select_related("application", "changed_by")
        )
