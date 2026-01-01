from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import (
                    Performance
                    )
from .serializers import (
                         PerformanceSerializer
                         )

from rest_framework import serializers, viewsets, permissions 


class PerformanceViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Product.objects.all()
     serializer_class = PerformanceSerializer
     def get_queryset(self):
          return Performance.objects.filter(company_id=self.request.user.company_id).order_by('-createDate')
     
     
