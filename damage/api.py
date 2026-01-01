from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from damage.models import (Damage,
                         DamageProduct,
                         DamageItem,
                         DamageCash,
                         DamageHistory
                         )
from .serializers import (
     DamageHistorySerialzer,
     DamageItemSerialzer,
     DamageProductPostSerializer,
     DamageProductSerializer
)
from rest_framework import serializers, viewsets, permissions 


class DamageProductViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Expense.objects.all()
     serializer_class = DamageProductSerializer
     # # http_method_names= ['get']
     def get_queryset(self):
          return DamageProduct.objects.filter(company_id=self.request.user.company_id)
     
     
class DamageProductPostViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Expense.objects.all()
     serializer_class = DamageProductPostSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return DamageProduct.objects.filter(company_id=self.request.user.company_id)
     
     
class DamageItemViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = DamageItemSerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return DamageItem.objects.all()
     
     
     
class DamageHistoryViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = DamageHistorySerialzer
     # http_method_names= ['get']
     def get_queryset(self):
          return DamageHistory.objects.filter(company_id=self.request.user.company_id)