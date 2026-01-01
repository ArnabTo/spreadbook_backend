from rest_framework.decorators import permission_classes
from .models import Portfolio
from .serializers import PortfolioSerializer
from rest_framework import serializers, viewsets, permissions 


class PortfolioViewSet(viewsets.ModelViewSet):
     queryset = Portfolio.objects.all()
     serializer_class = PortfolioSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()