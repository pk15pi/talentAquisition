from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Application,ApplicationHistory
from .serializers import ApplicationSerializer
from apps.common import RolePermission
class ApplicationViewSet(viewsets.ModelViewSet):
    queryset=Application.objects.select_related("candidate","job","recruiter").all().order_by("-created_at")
    serializer_class=ApplicationSerializer; permission_classes=[IsAuthenticated,RolePermission]
    allowed_roles=("ADMIN","MANAGEMENT","HR","TEAM_LEAD")
    def perform_create(self,serializer):
        app=serializer.save(recruiter=serializer.validated_data.get("recruiter") or self.request.user, sourced_by=serializer.validated_data.get("sourced_by") or self.request.user)
        ApplicationHistory.objects.create(application=app,new_status=app.status,changed_by=self.request.user,remarks="Application created")
    @action(detail=True,methods=["post"],url_path="change-status")
    def change_status(self,request,pk=None):
        app=self.get_object(); new=request.data.get("status")
        valid={v for v,_ in Application.Status.choices}
        if new not in valid: return Response({"detail":"Invalid status"},status=400)
        old=app.status
        with transaction.atomic():
            app.status=new
            if new=="SUBMITTED": app.submitted_at=timezone.now()
            if new=="SELECTED": app.selected_at=timezone.now()
            if new=="JOINED": app.joined_at=timezone.now()
            app.save()
            ApplicationHistory.objects.create(application=app,old_status=old,new_status=new,changed_by=request.user,remarks=request.data.get("remarks",""))
        return Response(self.get_serializer(app).data)
