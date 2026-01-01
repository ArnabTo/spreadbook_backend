
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import BillingAddress, Billing
User = get_user_model()




class BillingSerializer(serializers.ModelSerializer):
     class Meta:
          model = Billing
          fields = '__all__'
          

