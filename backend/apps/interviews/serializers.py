from rest_framework import serializers

from apps.access import visible_interviews

from .models import Interview, InterviewParticipant


class InterviewParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewParticipant
        fields = ("id", "interview", "user", "name", "role")
        read_only_fields = ("id",)

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

    class Meta:
        model = Interview
        fields = (
            "id",
            "application",
            "round_name",
            "interview_date",
            "interviewer_name",
            "feedback",
            "result",
            "created_by",
            "created_at",
            "participants",
        )
        read_only_fields = ("created_by", "created_at", "participants")
