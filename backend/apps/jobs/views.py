from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.access import user_has, visible_jobs
from apps.common import ModelActionPermission
from apps.matching.services import run_matching

from .models import Job, JobAssignment, JobAssignmentHistory, JobStatusHistory
from .serializers import JobSerializer


class JobViewSet(ModelViewSet):
    queryset = Job.objects.select_related("client", "sales_owner", "created_by").prefetch_related("assignments").all().order_by("-created_at")
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
    action_permissions = {
        "assign": "jobs.assign_recruiter",
        "match": "jobs.run_match",
    }

    def get_queryset(self):
        return (
            visible_jobs(self.request.user)
            .select_related("client", "sales_owner", "created_by")
            .prefetch_related("assignments")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        owner = serializer.validated_data.get("sales_owner")
        if owner is None or not user_has(self.request.user, "jobs.assign_job_owner"):
            owner = self.request.user
        if not owner.is_active:
            raise ValidationError({"sales_owner": "Choose an active user."})
        job = serializer.save(created_by=self.request.user, sales_owner=owner)
        JobStatusHistory.objects.create(
            job=job,
            old_status="",
            new_status=job.status,
            changed_by=self.request.user,
            remarks="JD created",
        )

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        old_owner = serializer.instance.sales_owner
        new_owner = serializer.validated_data.get("sales_owner", old_owner)
        if not user_has(self.request.user, "jobs.assign_job_owner"):
            new_owner = old_owner
        elif not new_owner.is_active:
            raise ValidationError({"sales_owner": "Choose an active user."})
        job = serializer.save(sales_owner=new_owner)
        if old_status != job.status:
            JobStatusHistory.objects.create(
                job=job,
                old_status=old_status,
                new_status=job.status,
                changed_by=self.request.user,
            )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None, **kwargs):
        job = self.get_object()
        ids = request.data.get("recruiter_ids", [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "recruiter_ids must be a non-empty list", "code": "invalid", "errors": None},
                status=400,
            )
        User = get_user_model()
        recruiters = list(User.objects.filter(id__in=ids, is_active=True))
        if len(recruiters) != len(set(str(value) for value in ids)) or any(
            not user.has_perm("jobs.be_assigned_recruiter") for user in recruiters
        ):
            return Response(
                {
                    "detail": "Every recruiter must be an active user who is allowed to be assigned.",
                    "code": "invalid",
                    "errors": None,
                },
                status=400,
            )
        created = []
        for recruiter in recruiters:
            obj, was_created = JobAssignment.objects.get_or_create(
                job=job,
                recruiter=recruiter,
                defaults={"assigned_by": request.user, "is_active": True},
            )
            if was_created:
                JobAssignmentHistory.objects.create(
                    job=job,
                    recruiter=recruiter,
                    action=JobAssignmentHistory.Action.ASSIGNED,
                    changed_by=request.user,
                )
            elif not obj.is_active:
                obj.is_active = True
                obj.assigned_by = request.user
                obj.save()
                JobAssignmentHistory.objects.create(
                    job=job,
                    recruiter=recruiter,
                    action=JobAssignmentHistory.Action.REACTIVATED,
                    changed_by=request.user,
                )
            created.append(str(obj.id))
        return Response({"assignment_ids": created})

    @action(detail=True, methods=["post"])
    def match(self, request, pk=None, **kwargs):
        # Scoring still crashes on Django 5.2 (see matching.services). Phase 4.
        job = self.get_object()
        run = run_matching(job, request.user)
        return Response(
            {
                "match_run_id": str(run.id),
                "candidates_processed": run.candidates_processed,
                "results": [
                    {
                        "candidate": str(result.candidate_id),
                        "candidate_code": result.candidate.candidate_code,
                        "name": result.candidate.full_name,
                        "score": float(result.overall_score),
                        "missing_mandatory_skills": result.missing_mandatory_skills,
                    }
                    for result in run.results.select_related("candidate").order_by("-overall_score")[:100]
                ],
            }
        )
