from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Billing, BillingAddress
from .serializers import BillingSerializer
from rest_framework import viewsets, permissions 



class BillingViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = BillingSerializer
     http_method_names= ['get']
     def get_queryset(self):
          return Billing.objects.filter(company_id=self.request.user.company_id).order_by('-createDate')
