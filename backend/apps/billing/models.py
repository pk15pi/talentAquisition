import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from decimal import Decimal
class Invoice(models.Model):
    class Status(models.TextChoices): DRAFT="DRAFT","Draft"; ISSUED="ISSUED","Issued"; PART_PAID="PART_PAID","Part Paid"; PAID="PAID","Paid"; OVERDUE="OVERDUE","Overdue"; VOID="VOID","Void"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); invoice_number=models.CharField(max_length=40,unique=True,blank=True)
    client=models.ForeignKey("clients.Client",on_delete=models.PROTECT,related_name="invoices")
    invoice_date=models.DateField(); due_date=models.DateField(); subtotal=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    tax_amount=models.DecimalField(max_digits=12,decimal_places=2,default=0); total=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.DRAFT); notes=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes=[models.Index(fields=["client","status"])]
        constraints=[models.CheckConstraint(condition=Q(subtotal__gte=0)&Q(tax_amount__gte=0)&Q(total__gte=0),name="invoice_amounts_nonnegative")]
    def save(self,*args,**kwargs):
        if not self.invoice_number:
            from django.utils.timezone import localdate
            from apps.organizations.utils import next_business_code
            year=localdate().year
            self.invoice_number=next_business_code(f"invoice-{year}",f"SW-INV-{year}-",4)
        super().save(*args,**kwargs)
    @property
    def paid_amount(self): return self.payments.aggregate(v=Sum("amount"))["v"] or Decimal("0.00")
    @property
    def credited_amount(self): return self.credit_notes.aggregate(v=Sum("amount"))["v"] or Decimal("0.00")
    @property
    def outstanding_amount(self): return self.total-self.paid_amount-self.credited_amount
    def recalculate_totals(self):
        subtotal=Decimal("0.00"); tax=Decimal("0.00")
        for line in self.lines.all():
            base=line.unit_amount*line.quantity
            subtotal += base
            tax += base*line.tax_rate/Decimal("100")
        self.subtotal=subtotal; self.tax_amount=tax; self.total=subtotal+tax
        self.save(update_fields=["subtotal","tax_amount","total"])
class InvoiceLine(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    invoice=models.ForeignKey(Invoice,on_delete=models.CASCADE,related_name="lines")
    placement=models.ForeignKey("placements.Placement",on_delete=models.PROTECT,null=True,blank=True)
    description=models.CharField(max_length=255); quantity=models.PositiveIntegerField(default=1)
    unit_amount=models.DecimalField(max_digits=12,decimal_places=2); tax_rate=models.DecimalField(max_digits=5,decimal_places=2,default=0)
    @property
    def line_total(self): return self.quantity*self.unit_amount
    def save(self,*args,**kwargs):
        super().save(*args,**kwargs)
        self.invoice.recalculate_totals()
    def delete(self,*args,**kwargs):
        invoice=self.invoice
        result=super().delete(*args,**kwargs)
        invoice.recalculate_totals()
        return result
class Payment(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    invoice=models.ForeignKey(Invoice,on_delete=models.PROTECT,related_name="payments")
    amount=models.DecimalField(max_digits=12,decimal_places=2); payment_date=models.DateField(); reference=models.CharField(max_length=100,blank=True)
    mode=models.CharField(max_length=30,blank=True); notes=models.TextField(blank=True); recorded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta: constraints=[models.CheckConstraint(condition=Q(amount__gt=0),name="payment_amount_positive")]
    def save(self,*args,**kwargs):
        super().save(*args,**kwargs)
        invoice=self.invoice
        if invoice.paid_amount >= invoice.total and invoice.total > 0: invoice.status="PAID"
        elif invoice.paid_amount > 0: invoice.status="PART_PAID"
        invoice.save(update_fields=["status"])
class CreditNote(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    invoice=models.ForeignKey(Invoice,on_delete=models.PROTECT,related_name="credit_notes")
    credit_note_number=models.CharField(max_length=40,unique=True,blank=True); amount=models.DecimalField(max_digits=12,decimal_places=2)
    reason=models.TextField(); issue_date=models.DateField(); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta: constraints=[models.CheckConstraint(condition=Q(amount__gt=0),name="credit_note_amount_positive")]
    def save(self,*args,**kwargs):
        if not self.credit_note_number:
            from django.utils.timezone import localdate
            from apps.organizations.utils import next_business_code
            year=localdate().year
            self.credit_note_number=next_business_code(f"credit-note-{year}",f"SW-CN-{year}-",4)
        super().save(*args,**kwargs)
