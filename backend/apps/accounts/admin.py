from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from apps.access import (
    GROUP_ADMINISTRATOR,
    GROUP_HR,
    GROUP_MANAGEMENT,
    GROUP_SALES,
    GROUP_TEAM_LEAD,
)
from apps.admin_access import NoDeleteMixin

from .models import User

PROTECTED_GROUPS = {
    GROUP_ADMINISTRATOR,
    GROUP_MANAGEMENT,
    GROUP_SALES,
    GROUP_HR,
    GROUP_TEAM_LEAD,
}


@admin.register(User)
class CustomUserAdmin(NoDeleteMixin, UserAdmin):
    """Deactivate with is_active. The admin does not delete accounts."""

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "employee_code",
        "role",
        "department",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_staff", "is_active", "is_superuser", "department")
    search_fields = ("username", "first_name", "last_name", "email", "employee_code", "phone")
    ordering = ("username",)
    date_hierarchy = "date_joined"
    list_select_related = ("department",)
    fieldsets = UserAdmin.fieldsets + (
        ("SynfoTalent", {"fields": ("employee_code", "role", "phone", "department", "date_joined_company")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("SynfoTalent", {"fields": ("employee_code", "role", "phone", "department", "date_joined_company")}),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.extend(["last_login", "date_joined"])
        if not request.user.is_superuser:
            readonly.extend(["is_superuser", "user_permissions"])
        return tuple(dict.fromkeys(readonly))


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class SynfoGroupAdmin(DjangoGroupAdmin):
    list_display = ("name", "permission_count")
    ordering = ("name",)
    search_fields = ("name",)

    @admin.display(description="Permissions")
    def permission_count(self, obj):
        return obj.permissions.count()

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.name in PROTECTED_GROUPS:
            return False
        return super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset.exclude(name__in=PROTECTED_GROUPS))
