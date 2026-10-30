from rest_framework import serializers
from .models import Job, JobAssignment
class JobAssignmentSerializer(serializers.ModelSerializer):
    class Meta: model=JobAssignment; fields="__all__"; read_only_fields=("assigned_by","assigned_at")
class JobSerializer(serializers.ModelSerializer):
    assignments=JobAssignmentSerializer(many=True,read_only=True)
    class Meta:
        model=Job; fields="__all__"; read_only_fields=("id","job_code","created_by","created_at","updated_at")
        extra_kwargs={"sales_owner":{"required":False}}
