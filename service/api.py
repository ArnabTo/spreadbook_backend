from rest_framework.decorators import permission_classes
from .models import ServiceItem
from .serializers import ServiceItemSerializer
from rest_framework import serializers, viewsets, permissions 


class ServiceItemViewSet(viewsets.ModelViewSet):
     queryset = ServiceItem.objects.all()
     serializer_class = ServiceItemSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()