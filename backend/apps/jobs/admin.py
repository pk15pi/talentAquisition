from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.access import visible_jobs
from apps.admin_access import (
    HistoryInlineMixin,
    NoDeleteMixin,
    ParentInlineMixin,
    ReadOnlyModelAdmin,
    perm,
    strip_fieldsets,
    users_holding,
)
from apps.matching.models import JobSkill

from .models import Job, JobAssignment, JobAssignmentHistory, JobStatusHistory


class JobAssignmentForm(forms.ModelForm):
    class Meta:
        model = JobAssignment
        fields = "__all__"

    def clean_recruiter(self):
        recruiter = self.cleaned_data.get("recruiter")
        if recruiter is None:
            return recruiter
        if not recruiter.is_active or not recruiter.has_perm("jobs.be_assigned_recruiter"):
            raise ValidationError("Choose an active user who can be assigned as a recruiter.")
        return recruiter


class JobSkillForm(forms.ModelForm):
    class Meta:
        model = JobSkill
        fields = "__all__"

    def clean_weight(self):
        weight = self.cleaned_data.get("weight")
        if weight is not None and not 1 <= weight <= 10:
            raise ValidationError("Weight must be between 1 and 10.")
        return weight


class JobAssignmentInline(ParentInlineMixin, admin.TabularInline):
    model = JobAssignment
    form = JobAssignmentForm
    extra = 0
    parent_view_permission = "jobs.view_job"
    edit_permission = "jobs.assign_recruiter"
    fields = ("recruiter", "is_active", "assigned_by", "assigned_at")
    readonly_fields = ("assigned_by", "assigned_at")
    show_change_link = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "recruiter":
            kwargs["queryset"] = users_holding("jobs", "be_assigned_recruiter")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class JobSkillInline(ParentInlineMixin, admin.TabularInline):
    model = JobSkill
    form = JobSkillForm
    extra = 0
    parent_view_permission = "matching.view_jobskill"
    edit_permission = "matching.change_jobskill"
    allow_delete = True
    autocomplete_fields = ("skill",)
    fields = ("skill", "is_mandatory", "weight")


class JobAssignmentHistoryInline(HistoryInlineMixin, admin.TabularInline):
    model = JobAssignmentHistory
    parent_view_permission = "jobs.view_job"
    fields = ("recruiter", "action", "changed_by", "created_at", "remarks")
    readonly_fields = fields
    ordering = ("-created_at",)
    verbose_name_plural = "Assignment history"


class JobStatusHistoryInline(HistoryInlineMixin, admin.TabularInline):
    model = JobStatusHistory
    parent_view_permission = "jobs.view_job"
    fields = ("old_status", "new_status", "changed_by", "changed_at", "remarks")
    readonly_fields = fields
    ordering = ("-changed_at",)
    verbose_name_plural = "Status history"


def record_job_assignment(request, assignment):
    """Save an assignment and append history. Does not delete the row."""
    recruiter = assignment.recruiter
    if not recruiter.is_active or not recruiter.has_perm("jobs.be_assigned_recruiter"):
        raise ValidationError("Choose an active user who can be assigned as a recruiter.")
    previous = None
    if assignment.pk:
        previous = JobAssignment.objects.filter(pk=assignment.pk).values("is_active", "recruiter_id").first()
    if not assignment.assigned_by_id or previous is None or previous["is_active"] != assignment.is_active:
        assignment.assigned_by = request.user
    with transaction.atomic():
        assignment.save()
        if previous is None:
            action = JobAssignmentHistory.Action.ASSIGNED if assignment.is_active else JobAssignmentHistory.Action.UNASSIGNED
            JobAssignmentHistory.objects.create(
                job_id=assignment.job_id,
                recruiter_id=assignment.recruiter_id,
                action=action,
                changed_by=request.user,
            )
            return
        if previous["recruiter_id"] != assignment.recruiter_id:
            JobAssignmentHistory.objects.create(
                job_id=assignment.job_id,
                recruiter_id=previous["recruiter_id"],
                action=JobAssignmentHistory.Action.UNASSIGNED,
                changed_by=request.user,
            )
            JobAssignmentHistory.objects.create(
                job_id=assignment.job_id,
                recruiter_id=assignment.recruiter_id,
                action=JobAssignmentHistory.Action.ASSIGNED if assignment.is_active else JobAssignmentHistory.Action.UNASSIGNED,
                changed_by=request.user,
            )
            return
        if previous["is_active"] and not assignment.is_active:
            action = JobAssignmentHistory.Action.UNASSIGNED
        elif not previous["is_active"] and assignment.is_active:
            action = JobAssignmentHistory.Action.REACTIVATED
        else:
            return
        JobAssignmentHistory.objects.create(
            job_id=assignment.job_id,
            recruiter_id=assignment.recruiter_id,
            action=action,
            changed_by=request.user,
        )


@admin.register(Job)
class JobAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("job_code", "title", "client", "status", "priority", "sales_owner", "positions", "created_at")
    list_filter = ("status", "priority", "work_mode")
    search_fields = ("job_code", "title", "location", "client__company_name", "client__client_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("client", "sales_owner")
    autocomplete_fields = ("client",)
    readonly_fields = ("job_code", "created_by", "created_at", "updated_at")
    inlines = (JobAssignmentInline, JobSkillInline, JobAssignmentHistoryInline, JobStatusHistoryInline)
    fieldsets = (
        (None, {"fields": ("job_code", "client", "title", "status", "priority", "positions")}),
        ("Description", {"fields": ("jd_text", "experience_min", "experience_max", "location", "work_mode", "notice_period_days")}),
        ("Compensation range", {"fields": ("salary_min", "salary_max")}),
        ("Commercial terms", {"fields": ("fee_type", "fee_value", "guarantee_period_days")}),
        ("Ownership", {"fields": ("sales_owner", "created_by", "opened_at", "closed_at", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=visible_jobs(request.user).values("pk"))
            .select_related("client", "sales_owner", "created_by")
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and not perm(request.user, "jobs.assign_job_owner"):
            readonly.append("sales_owner")
        return tuple(dict.fromkeys(readonly))

    def get_exclude(self, request, obj=None):
        excluded = set(super().get_exclude(request, obj) or ())
        if obj is None and not perm(request.user, "jobs.assign_job_owner"):
            excluded.add("sales_owner")
        return tuple(excluded) or None

    def get_fieldsets(self, request, obj=None):
        return strip_fieldsets(super().get_fieldsets(request, obj), set(self.get_exclude(request, obj) or ()))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sales_owner":
            from django.contrib.auth import get_user_model

            kwargs["queryset"] = get_user_model().objects.filter(is_active=True).order_by("username")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        previous_status = ""
        previous_owner_id = None
        if change:
            row = Job.objects.filter(pk=obj.pk).values("status", "sales_owner_id").first()
            previous_status = row["status"] if row else ""
            previous_owner_id = row["sales_owner_id"] if row else None
            if previous_owner_id != obj.sales_owner_id and not perm(request.user, "jobs.assign_job_owner"):
                obj.sales_owner_id = previous_owner_id
        else:
            if not obj.created_by_id:
                obj.created_by = request.user
            if not perm(request.user, "jobs.assign_job_owner") or not obj.sales_owner_id:
                obj.sales_owner = request.user
        super().save_model(request, obj, form, change)
        if not change or previous_status != obj.status:
            JobStatusHistory.objects.create(
                job=obj,
                old_status=previous_status if change else "",
                new_status=obj.status,
                changed_by=request.user,
                remarks="JD created" if not change else "Status changed in admin",
            )

    def save_formset(self, request, form, formset, change):
        if formset.model is JobAssignment:
            for obj in formset.save(commit=False):
                record_job_assignment(request, obj)
            formset.save_m2m()
            return
        super().save_formset(request, form, formset, change)


@admin.register(JobAssignment)
class JobAssignmentAdmin(NoDeleteMixin, admin.ModelAdmin):
    form = JobAssignmentForm
    list_display = ("job", "recruiter", "is_active", "assigned_by", "assigned_at")
    list_filter = ("is_active",)
    search_fields = ("job__job_code", "job__title", "recruiter__username", "recruiter__first_name", "recruiter__last_name")
    date_hierarchy = "assigned_at"
    ordering = ("-assigned_at",)
    list_select_related = ("job", "recruiter", "assigned_by")
    autocomplete_fields = ("job",)
    readonly_fields = ("assigned_by", "assigned_at")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(job__in=visible_jobs(request.user)).select_related("job", "recruiter", "assigned_by")

    def has_add_permission(self, request):
        return perm(request.user, "jobs.assign_recruiter")

    def has_change_permission(self, request, obj=None):
        return perm(request.user, "jobs.assign_recruiter")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "recruiter":
            kwargs["queryset"] = users_holding("jobs", "be_assigned_recruiter")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        record_job_assignment(request, obj)


@admin.register(JobAssignmentHistory)
class JobAssignmentHistoryAdmin(ReadOnlyModelAdmin):
    list_display = ("job", "recruiter", "action", "changed_by", "created_at")
    list_filter = ("action",)
    search_fields = ("job__job_code", "job__title", "remarks")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("job", "recruiter", "changed_by")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(job__in=visible_jobs(request.user)).select_related("job", "recruiter", "changed_by")


@admin.register(JobStatusHistory)
class JobStatusHistoryAdmin(ReadOnlyModelAdmin):
    list_display = ("job", "old_status", "new_status", "changed_by", "changed_at")
    search_fields = ("job__job_code", "job__title", "old_status", "new_status", "remarks")
    date_hierarchy = "changed_at"
    ordering = ("-changed_at",)
    list_select_related = ("job", "changed_by")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(job__in=visible_jobs(request.user)).select_related("job", "changed_by")
