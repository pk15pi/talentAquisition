from rest_framework import serializers

from .models import SystemConfiguration


class SystemConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfiguration
        fields = (
            "id",
            "candidate_retention_days",
            "application_retention_days",
            "resume_retention_days",
            "audit_log_retention_days",
            "privacy_notice_version",
            "privacy_notice_text",
            "updated_at",
        )
        read_only_fields = ("id", "updated_at")
