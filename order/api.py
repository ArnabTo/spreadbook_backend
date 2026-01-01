from rest_framework.decorators import permission_classes
from .models import Order, Item, Delivery, History, Timeline, Payment, ShippingAddres
from .serializers import OrderSerializer
from rest_framework import serializers, viewsets, permissions 
from rest_framework import generics
from django.shortcuts import render


class OrderViewSet(viewsets.ModelViewSet):
     # queryset = Order.objects.all()
     serializer_class = OrderSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Order.objects.all()

# class SalePostSet(viewsets.ModelViewSet):
#      # queryset = Product.objects.all()
#      serializer_class = SalePostSerializer
#      # http_method_names= ['get']
#      def get_queryset(self):
#           return Sale.objects.all()
     
     
     
# class SaleItemSet(viewsets.ModelViewSet):
#      # queryset = Product.objects.all()
#      serializer_class = InvoiceSerialzer
#      # http_method_names= ['get']
#      def get_queryset(self):
#           return InvoiceItem.objects.all()