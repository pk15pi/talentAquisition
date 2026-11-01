from django.contrib import admin

from .models import CodeSequence, Department, SystemConfiguration

admin.site.register([Department, CodeSequence])


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """The one place an administrator sets retention and the privacy notice."""

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

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
