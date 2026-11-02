import hashlib
import os

from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.common import ModelActionPermission, RequiresPermission

from .downloads import DOWNLOAD_MAX_AGE_SECONDS, download_path, make_download_token, read_download_token
from .models import Candidate, CandidateNote, DuplicateReview, Resume
from .reviews import queue_file_hash_reviews
from .serializers import (
    CandidateNoteSerializer,
    CandidateSerializer,
    DuplicateReviewSerializer,
    ResumeSerializer,
)


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


class DuplicateReviewViewSet(ReadOnlyModelViewSet):
    queryset = DuplicateReview.objects.select_related("candidate", "matched_candidate", "reviewed_by").order_by(
        "-created_at"
    )
    serializer_class = DuplicateReviewSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]
    action_permissions = {
        "list": "candidates.review_duplicate",
        "retrieve": "candidates.review_duplicate",
        "decide": "candidates.review_duplicate",
    }

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None, **kwargs):
        review = self.get_object()
        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            return Response(
                {
                    "detail": "approved must be true or false.",
                    "code": "invalid",
                    "errors": {"approved": ["Send a boolean."]},
                },
                status=400,
            )
        notes = request.data.get("notes") or ""
        from django.core.exceptions import PermissionDenied
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            review.decide(request.user, approved=approved, notes=notes)
        except PermissionDenied as exc:
            return Response({"detail": str(exc), "code": "permission_denied", "errors": None}, status=403)
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response({"detail": message, "code": "invalid", "errors": None}, status=400)
        review.refresh_from_db()
        return Response(self.get_serializer(review).data)


class ResumeDownloadLinkView(APIView):
    """Mint a short-lived signed URL. Does not return file bytes, hashes, or parsed text."""

    permission_classes = [IsAuthenticated, RequiresPermission]
    required_permission = "candidates.view_resume_content"

    def post(self, request, resume_id, **kwargs):
        resume = get_object_or_404(Resume, pk=resume_id)
        token = make_download_token(request.user, resume)
        return Response(
            {
                "download_path": download_path(token),
                "expires_in": DOWNLOAD_MAX_AGE_SECONDS,
                "resume_id": str(resume.id),
                "original_filename": resume.original_filename,
            }
        )


class ResumeSignedDownloadView(APIView):
    """Stream a resume for a signed token. Public /media/ URLs stay unrouted."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, **kwargs):
        token = request.query_params.get("token", "")
        parsed, error = read_download_token(token)
        if error or parsed is None:
            return Response(
                {
                    "detail": "Resume download link is invalid or has expired.",
                    "code": "invalid_download_link",
                    "errors": None,
                },
                status=403,
            )
        user_id, resume_id = parsed
        User = get_user_model()
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None or not user.has_perm("candidates.view_resume_content"):
            return Response(
                {
                    "detail": "You do not have permission to download this resume.",
                    "code": "permission_denied",
                    "errors": None,
                },
                status=403,
            )
        resume = Resume.objects.filter(pk=resume_id).first()
        if resume is None or not resume.file:
            return Response({"detail": "Resume file was not found.", "code": "not_found", "errors": None}, status=404)
        try:
            handle = resume.file.open("rb")
        except FileNotFoundError:
            return Response({"detail": "Resume file was not found.", "code": "not_found", "errors": None}, status=404)
        filename = os.path.basename(resume.original_filename or "resume")
        return FileResponse(handle, as_attachment=True, filename=filename)


class CandidateNoteViewSet(ModelViewSet):
    queryset = CandidateNote.objects.all()
    serializer_class = CandidateNoteSerializer
    permission_classes = [IsAuthenticated, ModelActionPermission]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
