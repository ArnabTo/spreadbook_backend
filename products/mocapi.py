from rest_framework.decorators import permission_classes
from .models.product_model import Product, Image, NewLabel, SaleLabel
from .models.rating_model import Rating
from .models.review_model import Review
from .serializers import ReviewSerializer, RatingSerializer
from .serializers import ListProductSerializer, PostProductSerializer, PictureSerializer, NewLavelSerializer, SaleLavelSerializer, UpdateProductSerializer
from rest_framework import serializers, viewsets, permissions 



from rest_framework import generics
from django.shortcuts import render

class ReviewViewSet(viewsets.ModelViewSet):
     # queryset = Product.objects.all()
     serializer_class = ReviewSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Review.objects.all()
     
class RatingViewSet(viewsets.ModelViewSet):
     # queryset = Product.objects.all()
     serializer_class = RatingSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Rating.objects.all()

class ListProductViewSet(viewsets.ModelViewSet):
     # queryset = Product.objects.all()
     serializer_class = ListProductSerializer
     # http_method_names= ['get']
     def get_queryset(self):
          return Product.objects.all()
     
     
class PostProductViewSet(viewsets.ModelViewSet):
     serializer_class = PostProductSerializer
     def get_queryset(self):
          return Product.objects.all()
     
class UpdateProductViewSet(viewsets.ModelViewSet):
     serializer_class = UpdateProductSerializer
     def get_queryset(self):
          return Product.objects.all()


class PicturePostSet(viewsets.ModelViewSet):
     serializer_class = PictureSerializer
     def get_queryset(self):
          return Image.objects.all()
     

class NewLabelSet(viewsets.ModelViewSet):
     serializer_class = NewLavelSerializer
     def get_queryset(self):
          return NewLabel.objects.all()
     

class SaleLabelSet(viewsets.ModelViewSet):
     serializer_class = SaleLavelSerializer
     def get_queryset(self):
          return SaleLabel.objects.all()
     

