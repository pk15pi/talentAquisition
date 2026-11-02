from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from apps.access import visible_clients
from apps.admin_access import NoDeleteMixin, perm
from apps.placements.models import Placement

from .models import CreditNote, Invoice, InvoiceLine, Payment
from .services import audit_billing, recompute_invoice_totals, save_credit_within_capacity, save_payment_within_capacity


def allowed_fk_queryset(request, field_name):
    if field_name == "placement":
        if not perm(request.user, "placements.view_placement"):
            return Placement.objects.none()
        return Placement.objects.select_related("application", "application__candidate")
    if field_name == "invoice":
        if not perm(request.user, "billing.view_invoice"):
            return Invoice.objects.none()
        return Invoice.objects.all()
    if field_name == "client":
        return visible_clients(request.user)
    return None


class BillingRelatedForm(forms.ModelForm):
    """Reject related rows the user is not allowed to see."""

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def _reject_unauthorized(self, field_name):
        value = self.cleaned_data.get(field_name)
        if value is None or self.request is None:
            return value
        allowed = allowed_fk_queryset(self.request, field_name)
        if allowed is None:
            return value
        if not allowed.filter(pk=value.pk).exists():
            raise ValidationError("You cannot select this record.")
        return value

    def clean_placement(self):
        return self._reject_unauthorized("placement")

    def clean_invoice(self):
        return self._reject_unauthorized("invoice")

    def clean_client(self):
        return self._reject_unauthorized("client")


class PermissionInline(admin.TabularInline):
    extra = 0
    form = BillingRelatedForm
    add_perm = ""
    change_perm = ""
    view_perm = ""
    show_change_link = True

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        base_form = formset.form

        class RequestForm(base_form):
            def __init__(self, *args, **form_kwargs):
                form_kwargs["request"] = request
                super().__init__(*args, **form_kwargs)

        formset.form = RequestForm
        return formset

    def has_add_permission(self, request, obj=None):
        return perm(request.user, self.add_perm)

    def has_change_permission(self, request, obj=None):
        return perm(request.user, self.change_perm)

    def has_view_permission(self, request, obj=None):
        return perm(request.user, self.view_perm) or perm(request.user, "billing.view_invoice")

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        allowed = allowed_fk_queryset(request, db_field.name)
        if allowed is not None:
            kwargs["queryset"] = allowed
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class InvoiceLineInline(PermissionInline):
    model = InvoiceLine
    add_perm = "billing.add_invoiceline"
    change_perm = "billing.change_invoiceline"
    view_perm = "billing.view_invoiceline"
    fields = ("placement", "description", "quantity", "unit_amount", "tax_rate")
    autocomplete_fields = ("placement",)


class PaymentInline(PermissionInline):
    model = Payment
    add_perm = "billing.add_payment"
    change_perm = "billing.change_payment"
    view_perm = "billing.view_payment"
    fields = ("amount", "payment_date", "reference", "mode", "notes", "recorded_by")
    readonly_fields = ("recorded_by",)


class CreditNoteInline(PermissionInline):
    model = CreditNote
    add_perm = "billing.add_creditnote"
    change_perm = "billing.change_creditnote"
    view_perm = "billing.view_creditnote"
    fields = ("credit_note_number", "amount", "issue_date", "reason", "created_by")
    readonly_fields = ("credit_note_number", "created_by")


class BillingModelAdmin(NoDeleteMixin, admin.ModelAdmin):
    form = BillingRelatedForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        class RequestForm(form):
            def __init__(self, *args, **form_kwargs):
                form_kwargs["request"] = request
                super().__init__(*args, **form_kwargs)

        return RequestForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        allowed = allowed_fk_queryset(request, db_field.name)
        if allowed is not None:
            kwargs["queryset"] = allowed
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Invoice)
class InvoiceAdmin(BillingModelAdmin):
    list_display = ("invoice_number", "client", "invoice_date", "due_date", "status", "total", "outstanding_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("invoice_number", "client__company_name", "client__client_code", "notes")
    date_hierarchy = "invoice_date"
    ordering = ("-created_at",)
    list_select_related = ("client", "created_by")
    autocomplete_fields = ("client",)
    readonly_fields = ("invoice_number", "created_by", "created_at", "subtotal", "tax_amount", "total")
    inlines = (InvoiceLineInline, PaymentInline, CreditNoteInline)

    @admin.display(description="Outstanding")
    def outstanding_amount(self, obj):
        return obj.outstanding_amount

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        recompute_invoice_totals(obj)
        audit_billing(request.user, "invoice_saved", obj, {"total": str(obj.total), "source": "admin"})

    def save_formset(self, request, form, formset, change):
        inline = next(item for item in self.get_inline_instances(request) if item.model is formset.model)
        instances = formset.save(commit=False)
        for obj in instances:
            creating = obj._state.adding
            if creating and not inline.has_add_permission(request):
                raise ValidationError("You cannot add this billing record.")
            if not creating and not inline.has_change_permission(request):
                raise ValidationError("You cannot change this billing record.")
            if isinstance(obj, Payment):
                if not obj.recorded_by_id:
                    obj.recorded_by = request.user
                if not save_payment_within_capacity(obj):
                    raise ValidationError("Payment cannot exceed the invoice outstanding amount.")
            elif isinstance(obj, CreditNote):
                if not obj.created_by_id:
                    obj.created_by = request.user
                if not save_credit_within_capacity(obj):
                    raise ValidationError("Credit note cannot exceed the invoice outstanding amount.")
            else:
                obj.save()
            if isinstance(obj, Payment):
                audit_billing(request.user, "payment_saved", obj, {"invoice_id": str(obj.invoice_id), "amount": str(obj.amount), "source": "admin"})
            if isinstance(obj, CreditNote):
                audit_billing(request.user, "credit_note_saved", obj, {"invoice_id": str(obj.invoice_id), "amount": str(obj.amount), "source": "admin"})
        formset.save_m2m()
        if form.instance.pk:
            recompute_invoice_totals(form.instance)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(BillingModelAdmin):
    list_display = ("invoice", "description", "quantity", "unit_amount", "tax_rate", "placement")
    search_fields = ("description", "invoice__invoice_number")
    ordering = ("invoice",)
    list_select_related = ("invoice", "placement", "placement__application", "placement__application__candidate")
    autocomplete_fields = ("invoice", "placement")


@admin.register(Payment)
class PaymentAdmin(BillingModelAdmin):
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
        if not save_payment_within_capacity(obj):
            raise ValidationError("Payment cannot exceed the invoice outstanding amount.")
        audit_billing(request.user, "payment_saved", obj, {"invoice_id": str(obj.invoice_id), "amount": str(obj.amount), "source": "admin"})


@admin.register(CreditNote)
class CreditNoteAdmin(BillingModelAdmin):
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
        if not save_credit_within_capacity(obj):
            raise ValidationError("Credit note cannot exceed the invoice outstanding amount.")
        audit_billing(request.user, "credit_note_saved", obj, {"invoice_id": str(obj.invoice_id), "amount": str(obj.amount), "source": "admin"})
