from django.contrib import admin

from apps.access import visible_clients
from apps.admin_access import (
    HistoryInlineMixin,
    NoDeleteMixin,
    ParentInlineMixin,
    ReadOnlyModelAdmin,
    perm,
    strip_fieldsets,
    users_holding,
)

from .models import Client, ClientActivity, ClientContact, ClientOwnershipHistory

ClientActivity._meta.verbose_name_plural = "client activities"


class ClientContactInline(ParentInlineMixin, admin.TabularInline):
    model = ClientContact
    extra = 0
    parent_view_permission = "clients.view_client"
    edit_permission = "clients.change_clientcontact"
    allow_delete = True
    fields = ("name", "designation", "email", "phone", "is_primary")
    show_change_link = True


class ClientActivityInline(ParentInlineMixin, admin.TabularInline):
    model = ClientActivity
    extra = 0
    parent_view_permission = "clients.view_client"
    edit_permission = "clients.add_clientactivity"
    fields = ("activity_type", "subject", "notes", "follow_up_at", "user", "created_at")
    readonly_fields = ("user", "created_at")
    ordering = ("-created_at",)

    def has_change_permission(self, request, obj=None):
        return False


class ClientOwnershipHistoryInline(HistoryInlineMixin, admin.TabularInline):
    model = ClientOwnershipHistory
    parent_view_permission = "clients.view_client"
    fields = ("old_owner", "new_owner", "changed_by", "changed_at", "remarks")
    readonly_fields = fields
    ordering = ("-changed_at",)
    verbose_name_plural = "Ownership history"


@admin.register(Client)
class ClientAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("client_code", "company_name", "status", "sales_owner", "industry", "created_at")
    list_filter = ("status",)
    search_fields = ("client_code", "company_name", "industry", "website")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("sales_owner",)
    readonly_fields = ("client_code", "created_by", "created_at", "updated_at")
    inlines = (ClientContactInline, ClientActivityInline, ClientOwnershipHistoryInline)
    fieldsets = (
        (None, {"fields": ("client_code", "company_name", "status", "industry", "website", "address")}),
        ("Ownership", {"fields": ("sales_owner", "created_by", "created_at", "updated_at")}),
        (
            "Commercial defaults",
            {"fields": ("default_fee_type", "default_fee_value", "default_guarantee_period_days")},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(pk__in=visible_clients(request.user).values("pk"))
            .select_related("sales_owner", "created_by")
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and not perm(request.user, "clients.assign_client_owner"):
            readonly.append("sales_owner")
        return tuple(dict.fromkeys(readonly))

    def get_exclude(self, request, obj=None):
        excluded = set(super().get_exclude(request, obj) or ())
        if obj is None and not perm(request.user, "clients.assign_client_owner"):
            excluded.add("sales_owner")
        return tuple(excluded) or None

    def get_fieldsets(self, request, obj=None):
        return strip_fieldsets(super().get_fieldsets(request, obj), set(self.get_exclude(request, obj) or ()))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sales_owner":
            extra = []
            match = getattr(request, "resolver_match", None)
            object_id = match.kwargs.get("object_id") if match else None
            if object_id:
                current = Client.objects.filter(pk=object_id).values_list("sales_owner_id", flat=True).first()
                if current:
                    extra.append(current)
            kwargs["queryset"] = users_holding("clients", "own_client", extra)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        previous_owner_id = None
        if change:
            previous_owner_id = Client.objects.filter(pk=obj.pk).values_list("sales_owner_id", flat=True).first()
            if previous_owner_id != obj.sales_owner_id and not perm(request.user, "clients.assign_client_owner"):
                obj.sales_owner_id = previous_owner_id
        else:
            if not obj.created_by_id:
                obj.created_by = request.user
            if not perm(request.user, "clients.assign_client_owner") or not obj.sales_owner_id:
                obj.sales_owner = request.user
        super().save_model(request, obj, form, change)
        if not change or previous_owner_id != obj.sales_owner_id:
            ClientOwnershipHistory.objects.create(
                client=obj,
                old_owner_id=previous_owner_id,
                new_owner_id=obj.sales_owner_id,
                changed_by=request.user,
                remarks="Initial client ownership" if not change else "Client ownership changed",
            )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if isinstance(obj, ClientActivity) and not obj.user_id:
                obj.user = request.user
            obj.save()
        formset.save_m2m()


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "designation", "email", "phone", "is_primary", "created_at")
    list_filter = ("is_primary",)
    search_fields = ("name", "email", "phone", "client__company_name", "client__client_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("client",)
    autocomplete_fields = ("client",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(client__in=visible_clients(request.user)).select_related("client")


@admin.register(ClientActivity)
class ClientActivityAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("client", "activity_type", "subject", "user", "follow_up_at", "created_at")
    list_filter = ("activity_type",)
    search_fields = ("subject", "notes", "client__company_name", "client__client_code")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("client", "user")
    autocomplete_fields = ("client",)
    readonly_fields = ("user", "created_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(client__in=visible_clients(request.user))
            .select_related("client", "user")
        )

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(ClientOwnershipHistory)
class ClientOwnershipHistoryAdmin(ReadOnlyModelAdmin):
    list_display = ("client", "old_owner", "new_owner", "changed_by", "changed_at")
    search_fields = ("client__company_name", "client__client_code", "remarks")
    date_hierarchy = "changed_at"
    ordering = ("-changed_at",)
    list_select_related = ("client", "old_owner", "new_owner", "changed_by")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(client__in=visible_clients(request.user))
            .select_related("client", "old_owner", "new_owner", "changed_by")
        )
