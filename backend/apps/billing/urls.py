from rest_framework.routers import DefaultRouter

from .views import CreditNoteViewSet, InvoiceLineViewSet, InvoiceViewSet, PaymentViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet)
router.register("invoice-lines", InvoiceLineViewSet)
router.register("payments", PaymentViewSet)
router.register("credit-notes", CreditNoteViewSet)
urlpatterns = router.urls
