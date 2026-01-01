from rest_framework.decorators import permission_classes
from .models import Post
from .serializers import BlogSerializer
from rest_framework import serializers, viewsets, permissions 


class PostViewSet(viewsets.ModelViewSet):
     queryset = Post.objects.all()
     serializer_class = BlogSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()