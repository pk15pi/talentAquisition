from rest_framework.routers import DefaultRouter
from .views import InterviewViewSet
router=DefaultRouter(); router.register("interviews",InterviewViewSet)
urlpatterns=router.urls
