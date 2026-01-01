from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "message",
            "priority",
            "timestamp",
            "read",
            "actionUrl",
            "actionLabel",
            "data",
        ]
        read_only_fields = fields
