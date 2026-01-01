from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import( WarrentyProductList,
                    RepairCash,
                    Repair,
                    EnquiryItems,
                    TestDetail,
                    RepairDetail,
                    TrialPeriod,
                    RepairHistory
                    )
from .serializers import (
                         WarrentyProductListSerialzer,
                         RepairCashSerialzer,
                         RepairHistorySerialzer,
                         EnquiryItemsSerialzer,
                         RepairSerializer,
                         RepairPostSerializer,
                         
                         )
from rest_framework import serializers, viewsets, permissions 
from rest_framework import generics
from django.shortcuts import render


class WarrentyProductListViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = WarrentyProductListSerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return WarrentyProductList.objects.filter(company_id=self.request.user.company_id).order_by('-createDate')


class RepairViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = RepairSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Repair.objects.filter(company_id=self.request.user.company_id)


class RepairPostSerializerViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]

     # queryset = Product.objects.all()
     serializer_class = RepairPostSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Repair.objects.filter(company_id=self.request.user.company_id)
     
     
class EnquiryItemsSerialzerViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = EnquiryItemsSerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return EnquiryItems.objects.all()
     

class RepairCashViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = RepairCashSerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return RepairCash.objects.filter(company_id=self.request.user.company_id)
     
     
class RepairHistoryHistoryViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = RepairHistorySerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return RepairHistory.objects.filter(company_id=self.request.user.company_id)