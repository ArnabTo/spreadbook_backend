from rest_framework.decorators import permission_classes
from .models import PeopleReview
from .serializers import PeopleReviewSerializer
from rest_framework import serializers, viewsets, permissions 


class PeopleReviewViewSet(viewsets.ModelViewSet):
     queryset = PeopleReview.objects.all()
     serializer_class = PeopleReviewSerializer
     lookup_field = 'slug'
     # # http_method_names= ['get']
     # def get_queryset(self):
     #      return Post.objects.all()