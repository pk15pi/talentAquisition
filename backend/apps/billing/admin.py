from django.contrib import admin
from .models import Invoice, InvoiceLine, Payment, CreditNote
admin.site.register([Invoice, InvoiceLine, Payment, CreditNote])
