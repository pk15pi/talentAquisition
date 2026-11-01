from django.contrib import admin

from apps.access import visible_opportunities
from apps.admin_access import NoDeleteMixin

from .models import SalesOpportunity


@admin.register(SalesOpportunity)
class SalesOpportunityAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("title", "client", "owner", "stage", "expected_value", "next_follow_up", "created_at")
    list_filter = ("stage",)
    search_fields = ("title", "notes", "client__company_name", "client__client_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("client", "owner")
    autocomplete_fields = ("client",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=visible_opportunities(request.user).values("pk"))
            .select_related("client", "owner")
        )

    def save_model(self, request, obj, form, change):
        from apps.admin_access import perm

        if not change and (not obj.owner_id or not perm(request.user, "sales.view_all_salesopportunity")):
            obj.owner = request.user
        super().save_model(request, obj, form, change)
