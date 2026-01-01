
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserNotification




class NotificationSerializer(serializers.ModelSerializer):
     class Meta:
          model = UserNotification
          fields = "__all__"
          
     
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
