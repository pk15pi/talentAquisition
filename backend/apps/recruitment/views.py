from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.access import visible_applications
from apps.common import INVALID_QUERY_ID, ModelActionPermission, query_uuid

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
        queryset = (
            Submission.objects.filter(application__in=visible_applications(self.request.user))
            .select_related(
                "application__candidate",
                "application__job",
                "submitted_by",
                "resume",
            )
            .order_by("-submission_date")
        )
        application_id = query_uuid(self.request.query_params.get("application"))
        if application_id is INVALID_QUERY_ID:
            return queryset.none()
        if application_id is not None:
            queryset = queryset.filter(application_id=application_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)
