from rest_framework import serializers
from .models import Candidate,Resume,CandidateNote
class ResumeSerializer(serializers.ModelSerializer):
    class Meta: model=Resume; fields="__all__"; read_only_fields=("id","uploaded_by","uploaded_at","parsing_status")
class CandidateSerializer(serializers.ModelSerializer):
    resumes=ResumeSerializer(many=True,read_only=True)
    class Meta: model=Candidate; fields="__all__"; read_only_fields=("id","candidate_code","sourced_by","normalized_email","normalized_phone","created_at","updated_at")
class CandidateNoteSerializer(serializers.ModelSerializer):
    class Meta: model=CandidateNote; fields="__all__"; read_only_fields=("user","created_at")
