from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Attendance, AttendanceData
from .serializers import AttendanceSerializer, AttendanceDataSerialzer
from rest_framework import serializers, viewsets, permissions 
from rest_framework import generics
from django.shortcuts import render


class AttendanceViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = AttendanceSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Attendance.objects.filter(company_id=self.request.user.company_id)