from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet,InvoiceLineViewSet,PaymentViewSet
router=DefaultRouter(); router.register("invoices",InvoiceViewSet); router.register("invoice-lines",InvoiceLineViewSet); router.register("payments",PaymentViewSet)
urlpatterns=router.urls
