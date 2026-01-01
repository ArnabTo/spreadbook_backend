from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import (
                    Return,
                    ReturnProduct,
                    ReturnProductHistory,
                    ReturnProductCash,
                    ReturnProductItem
                    )
from .serializers import (
                         ReturnSerializer,
                         ReturnProductHistorySerialzer,
                         ReturnProductItemSerialzer,
                         ReturnProductPostSerializer,
                         ReturnProductSerializer
                         )

from rest_framework import serializers, viewsets, permissions 


class ReturnViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = ReturnSerializer
     def get_queryset(self):
          return Return.objects.filter(company_id=self.request.user.company_id).order_by('-createDate')
     
     

class ReturnProductViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Expense.objects.all()
     serializer_class = ReturnProductSerializer
     # # http_method_names= ['get']
     def get_queryset(self):
          return ReturnProduct.objects.filter(company_id=self.request.user.company_id)
     
     
class ReturnProductPostViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Expense.objects.all()
     serializer_class = ReturnProductPostSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return ReturnProduct.objects.filter(company_id=self.request.user.company_id)
     
     
class ReturnProductItemViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = ReturnProductItemSerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return ReturnProductItem.objects.all()
     
     
     
class ReturnProductHistoryViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = ReturnProductHistorySerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return ReturnProductHistory.objects.filter(company_id=self.request.user.company_id)