from django.contrib import admin

from apps.admin_access import ReadOnlyModelAdmin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyModelAdmin):
    list_display = ("timestamp", "user", "action", "entity_type", "entity_id", "ip_address")
    list_filter = ("action", "entity_type")
    search_fields = ("action", "entity_type", "entity_id", "user__username")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    list_select_related = ("user",)
