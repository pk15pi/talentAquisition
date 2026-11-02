from rest_framework.routers import DefaultRouter

from .views import InterviewParticipantViewSet, InterviewViewSet

router = DefaultRouter()
router.register("interviews", InterviewViewSet)
router.register("interview-participants", InterviewParticipantViewSet)
urlpatterns = router.urls
