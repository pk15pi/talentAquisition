from rest_framework import serializers

from .models import CandidateSkill, JobSkill, MatchResult, MatchRun, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class CandidateSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = CandidateSkill
        fields = "__all__"
        read_only_fields = ("skill_name",)


class JobSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = JobSkill
        fields = "__all__"
        read_only_fields = ("skill_name",)


class MatchResultSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_code = serializers.CharField(source="candidate.candidate_code", read_only=True)
    mandatory_skill_failure = serializers.SerializerMethodField()

    class Meta:
        model = MatchResult
        fields = (
            "id",
            "candidate",
            "candidate_name",
            "candidate_code",
            "skills_score",
            "experience_score",
            "location_score",
            "responsibility_score",
            "notice_period_score",
            "overall_score",
            "missing_mandatory_skills",
            "mandatory_skill_failure",
            "explanation",
            "created_at",
        )
        read_only_fields = fields

    def get_mandatory_skill_failure(self, obj):
        if obj.missing_mandatory_skills:
            return True
        return bool((obj.explanation or {}).get("mandatory_skill_failure"))


class MatchRunSerializer(serializers.ModelSerializer):
    results = serializers.SerializerMethodField()

    class Meta:
        model = MatchRun
        fields = (
            "id",
            "job",
            "initiated_by",
            "engine_version",
            "candidates_processed",
            "started_at",
            "completed_at",
            "results",
        )
        read_only_fields = fields

    def get_results(self, obj):
        rows = obj.results.select_related("candidate").order_by("-overall_score", "candidate__full_name")
        return MatchResultSerializer(rows, many=True).data
