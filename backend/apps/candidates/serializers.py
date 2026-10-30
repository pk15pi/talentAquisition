from django.utils import timezone
from rest_framework import serializers

from apps.organizations.models import SystemConfiguration

from .models import Candidate, CandidateConsent, CandidateNote, Resume
from .reviews import queue_identity_duplicate_reviews


RESUME_CONTENT_FIELDS = ("file", "parsed_text", "file_hash")
COMPENSATION_FIELDS = ("current_ctc", "expected_ctc")


class ResumeSerializer(serializers.ModelSerializer):
    """Metadata only. File bytes, storage paths, hashes, and parsed text are not API fields."""

    class Meta:
        model = Resume
        fields = ("id", "original_filename", "version", "is_primary", "parsing_status", "uploaded_at")
        read_only_fields = fields


class CandidateSerializer(serializers.ModelSerializer):
    consent_acknowledged = serializers.BooleanField(write_only=True, required=False)
    resumes = ResumeSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = "__all__"
        read_only_fields = (
            "id",
            "candidate_code",
            "sourced_by",
            "normalized_email",
            "normalized_phone",
            "consent_recorded_at",
            "consent_withdrawn_at",
            "created_at",
            "updated_at",
            "current_ctc",
            "expected_ctc",
        )

    def _can_view_compensation(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.has_perm("candidates.view_candidate_compensation"))

    def validate(self, attrs):
        if not self._can_view_compensation():
            leaked = set(attrs) & set(COMPENSATION_FIELDS)
            if leaked:
                raise serializers.ValidationError("You do not have permission to set candidate compensation.")
        return self._validate_consent(attrs)

    def _validate_consent(self, attrs):
        if self.instance is None:
            if not attrs.get("consent_acknowledged"):
                raise serializers.ValidationError(
                    {"consent_acknowledged": "Candidate consent is required before a profile can be stored."}
                )
            version = (attrs.get("privacy_notice_version") or "").strip()
            if not version:
                raise serializers.ValidationError(
                    {"privacy_notice_version": "Record the privacy notice version the candidate accepted."}
                )
            config = SystemConfiguration.objects.first()
            if config and config.privacy_notice_version and version != config.privacy_notice_version:
                raise serializers.ValidationError(
                    {"privacy_notice_version": "Consent must match the current privacy notice version."}
                )
            attrs["privacy_notice_version"] = version
        else:
            attrs.pop("consent_acknowledged", None)
            attrs.pop("privacy_notice_version", None)
        return attrs

    def create(self, validated_data):
        validated_data.pop("consent_acknowledged", None)
        validated_data["consent_recorded_at"] = timezone.now()
        candidate = super().create(validated_data)
        CandidateConsent.objects.create(
            candidate=candidate,
            purpose="recruitment",
            processing_basis="consent",
            privacy_notice_version=candidate.privacy_notice_version,
            recorded_by=validated_data.get("sourced_by"),
            source="api",
        )
        queue_identity_duplicate_reviews(candidate)
        return candidate

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self._can_view_compensation():
            for field in COMPENSATION_FIELDS:
                data.pop(field, None)
        return data


class CandidateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateNote
        fields = "__all__"
        read_only_fields = ("user", "created_at")
