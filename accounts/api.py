from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models.bank_account_model import Bank, Transition
from .serializers import BankAccountSerializer, TransitionSerializer, GetTransitionSerializer
from rest_framework import serializers, viewsets, permissions 
from rest_framework import generics
from django.shortcuts import render


class BankAccountViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = BankAccountSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Bank.objects.filter(company_id=self.request.user.company_id)
     
     

class TransitionViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = TransitionSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Transition.objects.filter(company_id=self.request.user.company_id).order_by('-createdAt')
     

class GetTransitionViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = GetTransitionSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Transition.objects.filter(company_id=self.request.user.company_id).order_by('-createdAt')