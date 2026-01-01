
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import (
                    Performance
                    )
User = get_user_model()


class CreatorDetailsSerializer(serializers.ModelSerializer):
     class Meta:
          model = User
          fields = ['id', 'name', 'email',  'phoneNumber', 'company', 'role', 'payroll']
          depth = 1
          
          
class PerformanceSerializer(serializers.ModelSerializer):
     creator = CreatorDetailsSerializer(required=False)
     class Meta:
          model = Performance
          fields = "__all__"
          depth = 1
          
     def create(self, validated_data):
          performance =  Performance.objects.create( 
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        **validated_data
                                        )
          return performance
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)