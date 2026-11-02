from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.common import INVALID_QUERY_ID, ModelActionPermission, query_uuid

from .models import CandidateSkill, JobSkill, Skill
from .serializers import CandidateSkillSerializer, JobSkillSerializer, SkillSerializer


class SkillViewSet(ModelViewSet):
    queryset = Skill.objects.all().order_by("name")
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]


class CandidateSkillViewSet(ModelViewSet):
    queryset = CandidateSkill.objects.select_related("candidate", "skill").all()
    serializer_class = CandidateSkillSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        queryset = CandidateSkill.objects.select_related("candidate", "skill").order_by("skill__name")
        candidate_id = query_uuid(self.request.query_params.get("candidate"))
        if candidate_id is INVALID_QUERY_ID:
            return queryset.none()
        if candidate_id is not None:
            queryset = queryset.filter(candidate_id=candidate_id)
        return queryset


class JobSkillViewSet(ModelViewSet):
    queryset = JobSkill.objects.select_related("job", "skill").all()
    serializer_class = JobSkillSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def get_queryset(self):
        queryset = JobSkill.objects.select_related("job", "skill").order_by("skill__name")
        job_id = query_uuid(self.request.query_params.get("job"))
        if job_id is INVALID_QUERY_ID:
            return queryset.none()
        if job_id is not None:
            queryset = queryset.filter(job_id=job_id)
        return queryset
