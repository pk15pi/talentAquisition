from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Interview
from .serializers import InterviewSerializer
class InterviewViewSet(viewsets.ModelViewSet):
    queryset=Interview.objects.select_related("application").all().order_by("-interview_date")
    serializer_class=InterviewSerializer; permission_classes=[IsAuthenticated]
    def perform_create(self,serializer): serializer.save(created_by=self.request.user)
