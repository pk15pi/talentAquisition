from django.contrib import admin

from apps.admin_access import SensitiveModelAdmin, perm

from .models import Placement

FINANCIAL_FIELDS = (
    "offered_ctc",
    "agreed_fee_type",
    "agreed_fee_value",
    "expected_revenue",
    "guarantee_period_days",
)


@admin.register(Placement)
class PlacementAdmin(SensitiveModelAdmin):
    """HR can open a placement and cannot see or edit fee, CTC, or revenue fields."""

    sensitive_field_rules = (
        ("placements.view_placement_financials", FINANCIAL_FIELDS, "placements.change_placement_financials"),
    )
    list_display = (
        "placement_label",
        "status",
        "joining_date",
        "offered_ctc",
        "agreed_fee_type",
        "agreed_fee_value",
        "expected_revenue",
        "created_at",
    )
    list_display_links = ("placement_label",)
    list_filter = ("status",)
    search_fields = (
        "application__application_code",
        "application__candidate__full_name",
        "application__candidate__candidate_code",
        "application__job__title",
        "application__job__job_code",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("application", "application__candidate", "application__job")
    autocomplete_fields = ("application",)
    readonly_fields = ("created_at",)
    fields = (
        "application",
        "status",
        "joining_date",
        "offered_ctc",
        "agreed_fee_type",
        "agreed_fee_value",
        "expected_revenue",
        "guarantee_period_days",
        "created_at",
    )

    @admin.display(description="Placement", ordering="created_at")
    def placement_label(self, obj):
        application = obj.application
        return f"{application.application_code} — {application.candidate.full_name}"

    def has_add_permission(self, request):
        return super().has_add_permission(request) and perm(request.user, "placements.change_placement_financials")
