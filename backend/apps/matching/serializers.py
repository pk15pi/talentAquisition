from rest_framework import serializers
from .models import Skill,CandidateSkill,JobSkill
class SkillSerializer(serializers.ModelSerializer):
    class Meta: model=Skill; fields="__all__"
class CandidateSkillSerializer(serializers.ModelSerializer):
    class Meta: model=CandidateSkill; fields="__all__"
class JobSkillSerializer(serializers.ModelSerializer):
    class Meta: model=JobSkill; fields="__all__"
