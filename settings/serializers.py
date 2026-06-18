from rest_framework import serializers
from .models import SystemSettings, Branding


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class BrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branding
        fields = "__all__"
        read_only_fields = ("id", "updated_at")
