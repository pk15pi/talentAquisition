from rest_framework import serializers

from apps.access import visible_interviews

from .models import Interview, InterviewParticipant


class InterviewParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = InterviewParticipant
        fields = ("id", "interview", "user", "user_name", "name", "role")
        read_only_fields = ("id", "user_name")

    def get_user_name(self, obj):
        if not obj.user_id:
            return ""
        return obj.user.get_full_name() or obj.user.username

    def validate(self, attrs):
        interview = attrs.get("interview") or getattr(self.instance, "interview", None)
        user = attrs.get("user", getattr(self.instance, "user", None) if self.instance else None)
        name = attrs.get("name", getattr(self.instance, "name", "") if self.instance else "")
        if user is None and not (name or "").strip():
            raise serializers.ValidationError("A participant needs a user or a name.")
        request = self.context.get("request")
        if request and interview is not None and not visible_interviews(request.user).filter(pk=interview.pk).exists():
            raise serializers.ValidationError({"interview": "You cannot change participants on this interview."})
        return attrs


class InterviewSerializer(serializers.ModelSerializer):
    participants = InterviewParticipantSerializer(many=True, read_only=True)
    candidate_name = serializers.CharField(source="application.candidate.full_name", read_only=True)
    candidate_code = serializers.CharField(source="application.candidate.candidate_code", read_only=True)
    job_title = serializers.CharField(source="application.job.title", read_only=True)
    job_code = serializers.CharField(source="application.job.job_code", read_only=True)
    application_code = serializers.CharField(source="application.application_code", read_only=True)

    class Meta:
        model = Interview
        fields = (
            "id",
            "application",
            "application_code",
            "candidate_name",
            "candidate_code",
            "job_title",
            "job_code",
            "round_name",
            "interview_date",
            "interviewer_name",
            "feedback",
            "result",
            "created_by",
            "created_at",
            "participants",
        )
        read_only_fields = (
            "created_by",
            "created_at",
            "participants",
            "candidate_name",
            "candidate_code",
            "job_title",
            "job_code",
            "application_code",
        )
