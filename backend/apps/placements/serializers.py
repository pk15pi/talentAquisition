from rest_framework import serializers
from .models import Placement
class PlacementSerializer(serializers.ModelSerializer):
    class Meta: model=Placement; fields="__all__"
