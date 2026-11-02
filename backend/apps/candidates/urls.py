from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CandidateNoteViewSet,
    CandidateViewSet,
    DuplicateReviewViewSet,
    ResumeDownloadLinkView,
    ResumeSignedDownloadView,
)

router = DefaultRouter()
router.register("candidates", CandidateViewSet)
router.register("candidate-notes", CandidateNoteViewSet)
router.register("duplicate-reviews", DuplicateReviewViewSet)

urlpatterns = [
    path("resumes/<uuid:resume_id>/download/", ResumeDownloadLinkView.as_view(), name="resume-download-link"),
    path("resume-downloads/", ResumeSignedDownloadView.as_view(), name="resume-signed-download"),
    *router.urls,
]
