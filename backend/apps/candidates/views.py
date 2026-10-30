import hashlib

from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.common import ModelActionPermission

from .models import Candidate, CandidateNote, Resume
from .reviews import queue_file_hash_reviews
from .serializers import CandidateNoteSerializer, CandidateSerializer, ResumeSerializer


class CandidateViewSet(ModelViewSet):
    queryset = Candidate.objects.prefetch_related("resumes", "candidate_skills__skill").all().order_by("-created_at")
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
    action_permissions = {"upload_resume": "candidates.add_resume"}

    def perform_create(self, serializer):
        serializer.save(sourced_by=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        if query:
            queryset = (
                queryset.filter(full_name__icontains=query)
                | queryset.filter(email__icontains=query)
                | queryset.filter(location__icontains=query)
                | queryset.filter(candidate_skills__skill__name__icontains=query)
            )
        return queryset.distinct()

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="upload-resume")
    def upload_resume(self, request, pk=None, **kwargs):
        candidate = self.get_object()
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file is required", "code": "invalid", "errors": None}, status=400)
        if upload.size > 10 * 1024 * 1024:
            return Response({"detail": "Maximum file size is 10 MB", "code": "invalid", "errors": None}, status=400)
        extension = upload.name.lower().rsplit(".", 1)[-1] if "." in upload.name else ""
        if extension not in {"pdf", "docx"}:
            return Response({"detail": "Only PDF and DOCX files are supported", "code": "invalid", "errors": None}, status=400)
        digest = hashlib.sha256(upload.read()).hexdigest()
        upload.seek(0)
        version = (candidate.resumes.order_by("-version").values_list("version", flat=True).first() or 0) + 1
        resume = Resume.objects.create(
            candidate=candidate,
            file=upload,
            original_filename=upload.name,
            file_hash=digest,
            version=version,
            is_primary=not candidate.resumes.filter(is_primary=True).exists(),
            uploaded_by=request.user,
        )
        queue_file_hash_reviews(candidate, digest)
        from .tasks import parse_resume

        parse_resume.delay(resume.id)
        return Response(ResumeSerializer(resume).data, status=201)


class CandidateNoteViewSet(ModelViewSet):
    queryset = CandidateNote.objects.all()
    serializer_class = CandidateNoteSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
