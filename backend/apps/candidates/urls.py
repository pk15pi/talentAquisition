from rest_framework.routers import DefaultRouter
from .views import CandidateViewSet,CandidateNoteViewSet
router=DefaultRouter(); router.register("candidates",CandidateViewSet); router.register("candidate-notes",CandidateNoteViewSet)
urlpatterns=router.urls
