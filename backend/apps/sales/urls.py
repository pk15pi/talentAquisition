from rest_framework.routers import DefaultRouter
from .views import SalesOpportunityViewSet
router=DefaultRouter(); router.register("sales-opportunities",SalesOpportunityViewSet)
urlpatterns=router.urls
