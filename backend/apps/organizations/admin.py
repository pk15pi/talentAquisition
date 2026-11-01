from django.contrib import admin

from apps.admin_access import NoDeleteMixin, perm

from .models import CodeSequence, Department, SystemConfiguration


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "employee_count")
    search_fields = ("name",)
    ordering = ("name",)

    @admin.display(description="Employees")
    def employee_count(self, obj):
        return obj.employees.count()


@admin.register(CodeSequence)
class CodeSequenceAdmin(NoDeleteMixin, admin.ModelAdmin):
    """Issued business codes. Only an active superuser may move the counter."""

    list_display = ("key", "current_value")
    search_fields = ("key",)
    ordering = ("key",)
    fieldsets = (
        (
            None,
            {
                "description": (
                    "These counters issue client, job, candidate, application, invoice, "
                    "and credit-note codes. Changing a counter can reuse a code that was "
                    "already given out. Only an active superuser can edit one."
                ),
                "fields": ("key", "current_value"),
            },
        ),
    )

    def has_view_permission(self, request, obj=None):
        return perm(request.user, "organizations.view_codesequence")

    def has_add_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(NoDeleteMixin, admin.ModelAdmin):
    """The one place an administrator sets retention and the privacy notice."""

    list_display = ("__str__", "privacy_notice_version", "updated_at", "updated_by")
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    fields = (
        "candidate_retention_days",
        "application_retention_days",
        "resume_retention_days",
        "audit_log_retention_days",
        "privacy_notice_version",
        "privacy_notice_text",
        "updated_at",
        "updated_by",
    )
    readonly_fields = ("updated_at", "updated_by")

    def has_add_permission(self, request):
        if SystemConfiguration.objects.exists():
            return False
        return super().has_add_permission(request)

    def changelist_view(self, request, extra_context=None):
        if self.has_view_or_change_permission(request):
            SystemConfiguration.load()
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
