from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, ClientContactViewSet, ClientActivityViewSet
router=DefaultRouter(); router.register("clients",ClientViewSet); router.register("client-contacts",ClientContactViewSet); router.register("client-activities",ClientActivityViewSet)
urlpatterns=router.urls
