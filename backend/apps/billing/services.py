"""Invoice totals, payments, and credit notes.

Header totals written through the API are ignored. Line saves recompute the
header from the lines. Outstanding is total minus payments minus credit notes,
and payment status follows that figure. Each flow locks the invoice row.
"""

from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import CreditNote, Invoice

TWOPLACES = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def remaining_capacity(invoice, *, exclude_payment=None, exclude_credit=None) -> Decimal:
    payments = invoice.payments.all()
    if exclude_payment is not None and getattr(exclude_payment, "pk", None):
        payments = payments.exclude(pk=exclude_payment.pk)
    credits = invoice.credit_notes.all()
    if exclude_credit is not None and getattr(exclude_credit, "pk", None):
        credits = credits.exclude(pk=exclude_credit.pk)
    paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    credited = credits.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return _money(invoice.total - paid - credited)


def apply_payment_status(invoice):
    """Set PAID / PART_PAID from payments and credit notes. VOID stays VOID."""
    if invoice.status == Invoice.Status.VOID:
        return invoice
    paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    credited = invoice.credit_notes.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    outstanding = invoice.total - paid - credited
    if invoice.total > 0 and outstanding <= 0:
        new_status = Invoice.Status.PAID
    elif paid > 0 or credited > 0:
        new_status = Invoice.Status.PART_PAID
    elif invoice.status in {Invoice.Status.PAID, Invoice.Status.PART_PAID}:
        new_status = Invoice.Status.ISSUED
    else:
        new_status = invoice.status
    if new_status != invoice.status:
        invoice.status = new_status
        invoice.save(update_fields=["status"])
    return invoice


def recompute_invoice_totals(invoice):
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        subtotal = Decimal("0.00")
        tax = Decimal("0.00")
        for line in locked.lines.all():
            base = _money(line.unit_amount * line.quantity)
            subtotal += base
            tax += _money(base * line.tax_rate / Decimal("100"))
        locked.subtotal = _money(subtotal)
        locked.tax_amount = _money(tax)
        locked.total = _money(locked.subtotal + locked.tax_amount)
        locked.save(update_fields=["subtotal", "tax_amount", "total"])
        apply_payment_status(locked)
        invoice.subtotal = locked.subtotal
        invoice.tax_amount = locked.tax_amount
        invoice.total = locked.total
        invoice.status = locked.status
        return locked


def issue_credit_note(*, invoice, amount, reason, issue_date, user):
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        room = remaining_capacity(locked)
        if amount > room:
            raise ValidationError("Credit note cannot exceed the invoice outstanding amount.")
        note = CreditNote(
            invoice=locked,
            amount=amount,
            reason=reason,
            issue_date=issue_date,
            created_by=user,
        )
        note.save()
        apply_payment_status(locked)
        audit_billing(user, "credit_note_saved", note, {"invoice_id": str(locked.pk), "amount": str(note.amount), "created": True})
        return note


def audit_billing(user, action, obj, details=None):
    from apps.audit.services import record_audit

    record_audit(
        user=user,
        action=action,
        entity_type=obj._meta.label,
        entity_id=obj.pk,
        details=details or {},
    )


def save_payment_within_capacity(payment) -> bool:
    """Lock the invoice, reject an over-cap payment, and save inside that lock."""
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
        if payment.amount > remaining_capacity(locked, exclude_payment=payment if payment.pk else None):
            return False
        payment.save()
        return True


def save_credit_within_capacity(note) -> bool:
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=note.invoice_id)
        if note.amount > remaining_capacity(locked, exclude_credit=note if note.pk else None):
            return False
        note.save()
        return True


def update_credit_note(note, **changes):
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=note.invoice_id)
        amount = changes.get("amount", note.amount)
        room = remaining_capacity(locked, exclude_credit=note)
        if amount > room:
            raise ValidationError("Credit note cannot exceed the invoice outstanding amount.")
        for field, value in changes.items():
            setattr(note, field, value)
        note.save()
        apply_payment_status(locked)
        audit_billing(
            note.created_by,
            "credit_note_saved",
            note,
            {"invoice_id": str(locked.pk), "amount": str(note.amount), "created": False},
        )
        return note
