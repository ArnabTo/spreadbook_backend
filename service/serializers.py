from rest_framework import serializers
from .models import ServiceItem



class ServiceItemSerializer(serializers.ModelSerializer):
     class Meta:
          model = ServiceItem
          fields = '__all__'
          lookup_field = 'slug'
          extra_kwargs = {
               'url': {'lookup_field': 'slug'},
               # 'comments': {'required': False},
          }
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)