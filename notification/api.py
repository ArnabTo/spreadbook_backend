from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import UserNotification
from .serializers import NotificationSerializer
from rest_framework import serializers, viewsets, permissions 
from rest_framework import generics
from django.shortcuts import render


class NotificationViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = NotificationSerializer
     http_method_names= ['get']
     def get_queryset(self):
          return UserNotification.objects.filter(company_id=self.request.user.company_id).order_by('-createdAt')