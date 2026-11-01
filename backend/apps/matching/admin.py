from django.contrib import admin

from apps.access import visible_jobs
from apps.admin_access import HistoryInlineMixin, NoDeleteMixin, ParentInlineMixin, ReadOnlyModelAdmin

from .models import CandidateSkill, JobSkill, MatchResult, MatchRun, Skill, SkillAlias

SkillAlias._meta.verbose_name_plural = "skill aliases"


class SkillAliasInline(ParentInlineMixin, admin.TabularInline):
    model = SkillAlias
    extra = 0
    parent_view_permission = "matching.view_skill"
    edit_permission = "matching.change_skill"
    allow_delete = True
    fields = ("alias", "normalized_alias")
    readonly_fields = ("normalized_alias",)


@admin.register(Skill)
class SkillAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("name", "normalized_name", "category", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "normalized_name", "category")
    ordering = ("name",)
    inlines = (SkillAliasInline,)

    def save_model(self, request, obj, form, change):
        if not (obj.normalized_name or "").strip() and obj.name:
            obj.normalized_name = " ".join(obj.name.strip().lower().split())
        super().save_model(request, obj, form, change)


@admin.register(SkillAlias)
class SkillAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "normalized_alias", "skill")
    search_fields = ("alias", "normalized_alias", "skill__name")
    ordering = ("normalized_alias",)
    list_select_related = ("skill",)
    autocomplete_fields = ("skill",)
    readonly_fields = ("normalized_alias",)


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ("candidate", "skill", "experience_months")
    search_fields = ("candidate__full_name", "candidate__candidate_code", "skill__name")
    ordering = ("candidate", "skill")
    list_select_related = ("candidate", "skill")
    autocomplete_fields = ("candidate", "skill")


@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ("job", "skill", "is_mandatory", "weight")
    list_filter = ("is_mandatory",)
    search_fields = ("job__job_code", "job__title", "skill__name")
    ordering = ("job", "skill")
    list_select_related = ("job", "skill")
    autocomplete_fields = ("job", "skill")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(job__in=visible_jobs(request.user)).select_related("job", "skill")


class MatchResultInline(HistoryInlineMixin, admin.TabularInline):
    model = MatchResult
    parent_view_permission = "matching.view_matchrun"
    fields = (
        "candidate",
        "overall_score",
        "skills_score",
        "experience_score",
        "location_score",
        "responsibility_score",
        "notice_period_score",
        "created_at",
    )
    readonly_fields = fields
    ordering = ("-overall_score",)


@admin.register(MatchRun)
class MatchRunAdmin(ReadOnlyModelAdmin):
    """Stored runs only. Scoring stays in the matching service and is not edited here."""

    list_display = ("job", "initiated_by", "engine_version", "candidates_processed", "started_at", "completed_at")
    search_fields = ("job__job_code", "job__title", "engine_version")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    list_select_related = ("job", "initiated_by")
    inlines = (MatchResultInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(job__in=visible_jobs(request.user)).select_related("job", "initiated_by")


@admin.register(MatchResult)
class MatchResultAdmin(ReadOnlyModelAdmin):
    list_display = ("match_run", "candidate", "overall_score", "created_at")
    search_fields = ("candidate__full_name", "candidate__candidate_code", "match_run__job__job_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("match_run", "candidate")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(match_run__job__in=visible_jobs(request.user))
            .select_related("match_run", "candidate")
        )
