from rest_framework.routers import DefaultRouter
from .views import PlacementViewSet
router=DefaultRouter(); router.register("placements",PlacementViewSet)
urlpatterns=router.urls
