from django.contrib import admin

from apps.admin_access import NoDeleteMixin
from apps.access import visible_applications

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("application", "submitted_by", "resume", "response_status", "submission_date")
    list_filter = ("response_status",)
    search_fields = (
        "application__application_code",
        "application__candidate__full_name",
        "client_feedback",
        "response_status",
    )
    date_hierarchy = "submission_date"
    ordering = ("-submission_date",)
    list_select_related = ("application", "submitted_by", "resume")
    autocomplete_fields = ("application", "resume")
    readonly_fields = ("submission_date",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(application__in=visible_applications(request.user))
            .select_related("application", "submitted_by", "resume")
        )

    def save_model(self, request, obj, form, change):
        if not obj.submitted_by_id:
            obj.submitted_by = request.user
        super().save_model(request, obj, form, change)
