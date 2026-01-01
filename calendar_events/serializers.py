from rest_framework import serializers
from .models import Calendar


class CalendarSerializer(serializers.ModelSerializer):
     class Meta:
          model = Calendar
          fields = '__all__'
          # extra_kwargs = {
          #      'url': {'lookup_field': 'slug'},
          #      # 'comments': {'required': False},
          # }
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)