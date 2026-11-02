from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ("id", "username", "action", "entity_type", "entity_id", "details", "ip_address", "timestamp")
        read_only_fields = fields

    def get_username(self, obj):
        if not obj.user_id:
            return ""
        return obj.user.get_full_name() or obj.user.username
