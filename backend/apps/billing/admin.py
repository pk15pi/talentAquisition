from django.contrib import admin

from apps.admin_access import NoDeleteMixin

from .models import CreditNote, Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = ("placement", "description", "quantity", "unit_amount", "tax_rate")
    autocomplete_fields = ("placement",)
    show_change_link = True

    def has_delete_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("amount", "payment_date", "reference", "mode", "notes", "recorded_by")
    readonly_fields = ("recorded_by",)
    show_change_link = True

    def has_delete_permission(self, request, obj=None):
        return False


class CreditNoteInline(admin.TabularInline):
    model = CreditNote
    extra = 0
    fields = ("credit_note_number", "amount", "issue_date", "reason", "created_by")
    readonly_fields = ("credit_note_number", "created_by")
    show_change_link = True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("invoice_number", "client", "invoice_date", "due_date", "status", "total", "outstanding_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("invoice_number", "client__company_name", "client__client_code", "notes")
    date_hierarchy = "invoice_date"
    ordering = ("-created_at",)
    list_select_related = ("client", "created_by")
    autocomplete_fields = ("client",)
    readonly_fields = ("invoice_number", "created_by", "created_at")
    inlines = (InvoiceLineInline, PaymentInline, CreditNoteInline)

    @admin.display(description="Outstanding")
    def outstanding_amount(self, obj):
        return obj.outstanding_amount

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, Payment) and not obj.recorded_by_id:
                obj.recorded_by = request.user
            if isinstance(obj, CreditNote) and not obj.created_by_id:
                obj.created_by = request.user
            obj.save()
        formset.save_m2m()


@admin.register(InvoiceLine)
class InvoiceLineAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_amount", "tax_rate", "placement")
    search_fields = ("description", "invoice__invoice_number")
    ordering = ("invoice",)
    list_select_related = ("invoice", "placement")
    autocomplete_fields = ("invoice", "placement")


@admin.register(Payment)
class PaymentAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("invoice", "amount", "payment_date", "mode", "reference", "recorded_by")
    search_fields = ("reference", "invoice__invoice_number", "notes")
    date_hierarchy = "payment_date"
    ordering = ("-payment_date",)
    list_select_related = ("invoice", "recorded_by")
    autocomplete_fields = ("invoice",)
    readonly_fields = ("recorded_by",)

    def save_model(self, request, obj, form, change):
        if not obj.recorded_by_id:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CreditNote)
class CreditNoteAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ("credit_note_number", "invoice", "amount", "issue_date", "created_by")
    search_fields = ("credit_note_number", "invoice__invoice_number", "reason")
    date_hierarchy = "issue_date"
    ordering = ("-issue_date",)
    list_select_related = ("invoice", "created_by")
    autocomplete_fields = ("invoice",)
    readonly_fields = ("credit_note_number", "created_by")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
