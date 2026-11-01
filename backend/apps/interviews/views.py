from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.access import visible_interviews
from apps.common import ModelActionPermission

from .models import Interview
from .serializers import InterviewSerializer


class InterviewViewSet(ModelViewSet):
    queryset = Interview.objects.select_related("application").all().order_by("-interview_date")
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        return visible_interviews(self.request.user).select_related("application").order_by("-interview_date")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.instance._changed_by = self.request.user
        serializer.save()
