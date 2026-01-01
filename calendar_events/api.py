from rest_framework.decorators import permission_classes
from .models import Calendar
from .serializers import CalendarSerializer
from rest_framework import serializers, viewsets, permissions 


class CalendarViewSet(viewsets.ModelViewSet):
     queryset = Calendar.objects.all()
     serializer_class = CalendarSerializer
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()