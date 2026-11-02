from rest_framework import serializers

from apps.access import visible_applications

from .models import Submission
from .services import PENDING, submission_status_allowed


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = (
            "id",
            "application",
            "submitted_by",
            "resume",
            "submission_date",
            "client_feedback",
            "response_status",
        )
        read_only_fields = ("id", "submitted_by", "submission_date")

    def validate(self, attrs):
        application = attrs.get("application") or getattr(self.instance, "application", None)
        resume = attrs.get("resume") or getattr(self.instance, "resume", None)
        if application and resume and resume.candidate_id != application.candidate_id:
            raise serializers.ValidationError(
                {"resume": "The resume must belong to the application's candidate."}
            )
        request = self.context.get("request")
        if request and self.instance is None and application is not None:
            if not visible_applications(request.user).filter(pk=application.pk).exists():
                raise serializers.ValidationError({"application": "You cannot submit this application."})
        if self.instance is not None:
            if "application" in attrs and attrs["application"].pk != self.instance.application_id:
                raise serializers.ValidationError({"application": "The application on a submission cannot be changed."})
            if "resume" in attrs and attrs["resume"].pk != self.instance.resume_id:
                raise serializers.ValidationError({"resume": "The resume on a submission cannot be changed."})
            new_status = attrs.get("response_status", self.instance.response_status)
            if not submission_status_allowed(self.instance.response_status, new_status):
                raise serializers.ValidationError(
                    {
                        "response_status": (
                            f"Cannot move a submission from {self.instance.response_status} to {new_status}."
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        validated_data["response_status"] = PENDING
        return super().create(validated_data)
