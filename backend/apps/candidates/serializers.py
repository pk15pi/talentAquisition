from django.utils import timezone
from rest_framework import serializers

from apps.organizations.models import SystemConfiguration

from .models import Candidate, CandidateConsent, CandidateNote, Resume
from .reviews import queue_identity_duplicate_reviews


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = "__all__"
        read_only_fields = ("id", "uploaded_by", "uploaded_at", "parsing_status")


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
        )

    def validate(self, attrs):
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


class CandidateNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateNote
        fields = "__all__"
        read_only_fields = ("user", "created_at")
