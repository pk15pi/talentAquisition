from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.access import visible_applications
from apps.common import ModelActionPermission

from .models import Submission
from .serializers import SubmissionSerializer


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.select_related("application", "submitted_by", "resume").order_by("-submission_date")
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
    action_permissions = {
        "list": "recruitment.view_submission",
        "retrieve": "recruitment.view_submission",
        "create": "recruitment.add_submission",
        "update": "recruitment.change_submission",
        "partial_update": "recruitment.change_submission",
    }

    def get_queryset(self):
        return (
            Submission.objects.filter(application__in=visible_applications(self.request.user))
            .select_related("application", "submitted_by", "resume")
            .order_by("-submission_date")
        )

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)
