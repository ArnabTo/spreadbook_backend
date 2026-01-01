from rest_framework.decorators import permission_classes
from .models import Project
from .serializers import ProjectSerializer
from rest_framework import serializers, viewsets, permissions 


class ProjectViewSet(viewsets.ModelViewSet):
     queryset = Project.objects.all()
     serializer_class = ProjectSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()