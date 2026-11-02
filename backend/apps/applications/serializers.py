from rest_framework import serializers

from .models import Application, ApplicationHistory


class ApplicationHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationHistory
        fields = (
            "id",
            "old_status",
            "new_status",
            "changed_by",
            "changed_by_name",
            "remarks",
            "changed_at",
        )
        read_only_fields = fields

    def get_changed_by_name(self, obj):
        if not obj.changed_by_id:
            return ""
        return obj.changed_by.get_full_name() or obj.changed_by.username


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_code = serializers.CharField(source="candidate.candidate_code", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_code = serializers.CharField(source="job.job_code", read_only=True)
    recruiter_name = serializers.SerializerMethodField()
    history = ApplicationHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "application_code",
            "candidate",
            "candidate_name",
            "candidate_code",
            "job",
            "job_title",
            "job_code",
            "recruiter",
            "recruiter_name",
            "sourced_by",
            "status",
            "match_score",
            "contacted_at",
            "submitted_at",
            "selected_at",
            "joined_at",
            "created_at",
            "updated_at",
            "history",
        )
        read_only_fields = (
            "id",
            "application_code",
            "status",
            "recruiter",
            "sourced_by",
            "created_at",
            "updated_at",
            "candidate_name",
            "candidate_code",
            "job_title",
            "job_code",
            "recruiter_name",
            "history",
        )

    def get_recruiter_name(self, obj):
        if not obj.recruiter_id:
            return ""
        return obj.recruiter.get_full_name() or obj.recruiter.username
