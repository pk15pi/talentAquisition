from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.access import visible_interviews
from apps.common import INVALID_QUERY_ID, ModelActionPermission, query_uuid

from .models import Interview, InterviewParticipant
from .serializers import InterviewParticipantSerializer, InterviewSerializer


class InterviewViewSet(ModelViewSet):
    queryset = Interview.objects.select_related("application").all().order_by("-interview_date")
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        queryset = (
            visible_interviews(self.request.user)
            .select_related("application__candidate", "application__job", "created_by")
            .order_by("-interview_date")
        )
        application_id = query_uuid(self.request.query_params.get("application"))
        if application_id is INVALID_QUERY_ID:
            return queryset.none()
        if application_id is not None:
            queryset = queryset.filter(application_id=application_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.instance._changed_by = self.request.user
        serializer.save()


class InterviewParticipantViewSet(ModelViewSet):
    queryset = InterviewParticipant.objects.select_related("interview", "user")
    serializer_class = InterviewParticipantSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
    action_permissions = {
        "list": "interviews.view_interview",
        "retrieve": "interviews.view_interview",
        "create": "interviews.add_interview",
        "update": "interviews.change_interview",
        "partial_update": "interviews.change_interview",
    }

    def get_queryset(self):
        return (
            InterviewParticipant.objects.filter(interview__in=visible_interviews(self.request.user))
            .select_related("interview", "user")
            .order_by("interview_id", "name")
        )

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise ValidationError("That user is already a participant on this interview.") from exc
