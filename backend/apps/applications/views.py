from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.access import visible_applications
from apps.common import ModelActionPermission

from .models import Application, ApplicationHistory
from .serializers import ApplicationSerializer


class ApplicationViewSet(ModelViewSet):
    queryset = Application.objects.select_related("candidate", "job", "recruiter").all().order_by("-created_at")
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
    action_permissions = {"change_status": "applications.change_application"}

    def get_queryset(self):
        return visible_applications(self.request.user).select_related("candidate", "job", "recruiter").order_by("-created_at")

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                app = serializer.save(
                    recruiter=serializer.validated_data.get("recruiter") or self.request.user,
                    sourced_by=serializer.validated_data.get("sourced_by") or self.request.user,
                )
                ApplicationHistory.objects.create(
                    application=app,
                    new_status=app.status,
                    changed_by=self.request.user,
                    remarks="Application created",
                )
        except IntegrityError as exc:
            raise ValidationError(
                {
                    "detail": "This candidate already has an active application for this job. "
                    "A rejected or withdrawn application stays in history and can be followed by a new one."
                }
            ) from exc

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None, **kwargs):
        app = self.get_object()
        new = request.data.get("status")
        valid = {value for value, _label in Application.Status.choices}
        if new not in valid:
            return Response({"detail": "Invalid status", "code": "invalid", "errors": None}, status=400)
        old = app.status
        try:
            with transaction.atomic():
                app.status = new
                if new == "CONTACTED" and not app.contacted_at:
                    app.contacted_at = timezone.now()
                if new == "SUBMITTED":
                    app.submitted_at = timezone.now()
                if new == "SELECTED":
                    app.selected_at = timezone.now()
                if new == "JOINED":
                    app.joined_at = timezone.now()
                app.save()
                ApplicationHistory.objects.create(
                    application=app,
                    old_status=old,
                    new_status=new,
                    changed_by=request.user,
                    remarks=request.data.get("remarks", ""),
                )
        except IntegrityError as exc:
            raise ValidationError(
                {"detail": "Another active application already exists for this candidate and job."}
            ) from exc
        return Response(self.get_serializer(app).data)
