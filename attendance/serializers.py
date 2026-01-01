from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from authenticator.models import User as GenUser
from .models import AttendanceData, Attendance
User = get_user_model()


class PersonSerializer(serializers.ModelSerializer):
     class Meta:
          model = GenUser
          fields = ['id', 'name', 'email',
                    'phoneNumber',
                    'avatarUrl',
                    'role',
                    # 'payroll', 
                    # 'company_id'
                    ]
          extra_kwargs = {'password': {'required': False},
                         'email': {'required': False},
                         'name': {'required': False},
                         }
          

class AttendanceDataSerialzer(serializers.ModelSerializer):
     id = serializers.IntegerField(required=False)
     class Meta:
          model = AttendanceData
          fields = '__all__'
          read_only_fields = ('attendance_data',)
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     

class AttendanceSerializer(serializers.ModelSerializer):
     person = PersonSerializer(required=False)
     class Meta:
          model = Attendance
          fields = "__all__"
          
     
     def create(self, validated_data):
          attendance =  Attendance.objects.create( 
                                        company_id=self.context['request'].user.company_id,
                                        creator= self.context['request'].user,
                                        company= self.context['request'].user.company,
                                        **validated_data
                                        )
          return attendance
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
