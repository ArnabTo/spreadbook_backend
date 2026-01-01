from rest_framework.decorators import permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Changelog
from .serializers import ChangelogSerializer
from rest_framework import serializers, viewsets, permissions 


class ChangelogViewSet(viewsets.ModelViewSet):
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     # queryset = Post.objects.all()
     serializer_class = ChangelogSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     def get_queryset(self):
          # return Changelog.objects.filter(company_id=self.request.user.company_id)
          return Changelog.objects.order_by('-createdAt')