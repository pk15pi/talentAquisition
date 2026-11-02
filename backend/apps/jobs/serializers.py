from rest_framework import serializers
from .models import Job, JobAssignment
class JobAssignmentSerializer(serializers.ModelSerializer):
    recruiter_name=serializers.SerializerMethodField()
    class Meta: model=JobAssignment; fields="__all__"; read_only_fields=("assigned_by","assigned_at","recruiter_name")
    def get_recruiter_name(self,obj):
        if not obj.recruiter_id: return ""
        return obj.recruiter.get_full_name() or obj.recruiter.username
class JobSerializer(serializers.ModelSerializer):
    assignments=JobAssignmentSerializer(many=True,read_only=True)
    client_name=serializers.SerializerMethodField()
    sales_owner_name=serializers.SerializerMethodField()
    class Meta:
        model=Job; fields="__all__"; read_only_fields=("id","job_code","created_by","created_at","updated_at","client_name","sales_owner_name")
        extra_kwargs={"sales_owner":{"required":False}}
    def get_client_name(self,obj):
        return obj.client.company_name if obj.client_id else ""
    def get_sales_owner_name(self,obj):
        if not obj.sales_owner_id: return ""
        return obj.sales_owner.get_full_name() or obj.sales_owner.username
