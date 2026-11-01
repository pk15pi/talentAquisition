from django.contrib import admin

from apps.access import visible_interviews
from apps.admin_access import HistoryInlineMixin, NoDeleteMixin, ParentInlineMixin, ReadOnlyModelAdmin, perm

from .models import Interview, InterviewEvent, InterviewParticipant


class InterviewParticipantInline(ParentInlineMixin, admin.TabularInline):
    model = InterviewParticipant
    extra = 0
    parent_view_permission = "interviews.view_interview"
    edit_permission = "interviews.change_interview"
    fields = ("user", "name", "role")

    def has_delete_permission(self, request, obj=None):
        return perm(request.user, "interviews.change_interview")


class InterviewEventInline(HistoryInlineMixin, admin.TabularInline):
    model = InterviewEvent
    parent_view_permission = "interviews.view_interview"
    fields = ("event_type", "old_value", "new_value", "changed_by", "created_at")
    readonly_fields = fields
    ordering = ("-created_at",)
    verbose_name_plural = "Events"


@admin.register(Interview)
class InterviewAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("round_name", "application", "interview_date", "result", "interviewer_name", "created_at")
    list_filter = ("result",)
    search_fields = (
        "round_name",
        "interviewer_name",
        "application__application_code",
        "application__candidate__full_name",
    )
    date_hierarchy = "interview_date"
    ordering = ("-interview_date",)
    list_select_related = ("application", "application__candidate", "created_by")
    autocomplete_fields = ("application",)
    readonly_fields = ("created_by", "created_at")
    inlines = (InterviewParticipantInline, InterviewEventInline)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=visible_interviews(request.user).values("pk"))
            .select_related("application", "application__candidate", "created_by")
        )

    def save_model(self, request, obj, form, change):
        obj._changed_by = request.user
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InterviewParticipant)
class InterviewParticipantAdmin(admin.ModelAdmin):
    list_display = ("interview", "user", "name", "role")
    search_fields = ("name", "role", "interview__round_name", "user__username")
    ordering = ("interview", "name")
    list_select_related = ("interview", "user")
    autocomplete_fields = ("interview",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(interview__in=visible_interviews(request.user)).select_related("interview", "user")


@admin.register(InterviewEvent)
class InterviewEventAdmin(ReadOnlyModelAdmin):
    list_display = ("interview", "event_type", "changed_by", "created_at")
    list_filter = ("event_type",)
    search_fields = ("interview__round_name", "interview__application__application_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("interview", "changed_by")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(interview__in=visible_interviews(request.user)).select_related("interview", "changed_by")
