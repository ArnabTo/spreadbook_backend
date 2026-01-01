from decimal import Clamped
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Category
from .models.product_model import Product, NewLabel, SaleLabel, Size, Image, Tag, Color
from .models.rating_model import Rating
from .models.review_model import Review
from .function import attempt_json_deserialize
User = get_user_model()


class SizeSerializer(serializers.ModelSerializer):
     class Meta:
          model = Size
          fields = '__all__'
          
class ColorSerializer(serializers.ModelSerializer):
     class Meta:
          model = Color
          fields = '__all__'

class NewLavelSerializer(serializers.ModelSerializer):
     class Meta:
          model = NewLabel
          fields = ['pk' ,'enabled', 'content']
          
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)

class SaleLavelSerializer(serializers.ModelSerializer):
     class Meta:
          model = SaleLabel
          fields = ['pk', 'enabled', 'content']
          
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
# Update
class NewLavelUpdateSerializer(serializers.ModelSerializer):
     class Meta:
          model = NewLabel
          fields = ['pk', 'enabled', 'content']
          
          

class SaleLavelUpdateSerializer(serializers.ModelSerializer):
     class Meta:
          model = SaleLabel
          fields = ['pk', 'enabled', 'content']
          
#

class CategorySerializer(serializers.ModelSerializer):
     class Meta:
          model = Category
          fields = '__all__'

class PictureSerializer(serializers.ModelSerializer):
     class Meta:
          model = Image
          fields = '__all__'
          
     def create(self, validated_data):
          image = Image.objects.create(**validated_data)
          # print(**validated_data)
          return image
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)
     

class RatingSerializer(serializers.ModelSerializer):
     class Meta:
          model = Rating
          fields = ['name', 'starCount', ]
          
          
          
class ReviewSerializer(serializers.ModelSerializer):
     class Meta:
          model = Review
          fields = '__all__'
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)


class TagSerializer(serializers.ModelSerializer):
     class Meta:
          model = Tag
          fields = '__all__'


class ListProductSerializer(serializers.ModelSerializer):
     # category = CategorySerializer()
     newLabel = NewLavelSerializer(required=False)
     saleLabel = SaleLavelSerializer(required=False)
     # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
     images = PictureSerializer(many=True, required=False)
     sizes = serializers.StringRelatedField(many=True, required=False)
     ratings = RatingSerializer(many = True, required=False)
     reviews = ReviewSerializer(many = True, required=False)
     tags = serializers.StringRelatedField(many = True, required=False)
     colors = serializers.StringRelatedField(many=True, required=False)
     
     class Meta:
          model = Product
          fields = '__all__'
          
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)


class PostProductSerializer(serializers.ModelSerializer):
     # category = serializers.StringRelatedField(many=True)
     # newLabel = NewLavelUpdateSerializer() #f
     # saleLabel = SaleLavelUpdateSerializer() #f
     # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
     # images = PictureSerializer(many=True, read_only=True) #m
     # uploaded_images = serializers.ListField(
     #      child = serializers.ImageField(max_length = 1000000, allow_empty_file = False, use_url = False),
     #      write_only=True)
     # sizes = SizeSerializer(many=True, required=False) #mt
     # ratings = RatingSerializer(many = True, required=False)
     # reviews = ReviewSerializer(many = True, required=False)
     # tags = TagSerializer(many = True, required=False)
     # colors = ColorSerializer(many=True, required=False)
     
     class Meta:
          model = Product
          fields = '__all__'
          
          
     #  def create(self, validated_data):
     #      return super().create(validated_data)
          

     def create(self, validated_data):
          # uploaded_images = validated_data.pop("uploaded_images")
          # images_data = validated_data.pop('images')
          # newlabel_data = validated_data.pop('newLabel')
          # salelabel_data = validated_data.pop('saleLabel')
          # newLabel = NewLabel.objects.create(**newlabel_data)
          # saleLabel = SaleLabel.objects.create(**salelabel_data)
          
          # product = Product.objects.create(newLabel=newLabel, saleLabel=saleLabel, **validated_data)
          product = Product.objects.create(**validated_data)
          # for imgae in uploaded_images:
          #      newproduct_image = Image.objects.create(product=product, picture=imgae)
          # print(images_data)
          # for image_data in uploaded_images:
          #      Image.objects.create(product=product, picture=image_data)
          return product


     def update(self, instance, validated_data):
          newlabel = validated_data.pop('newLabel', None)
          salelabel = validated_data.pop('saleLabel', None)
          
          newlabel_serializer = self.fields['newLabel']
          newlabel_instance = instance.newLabel
          newlabel_serializer.update(newlabel_instance, newlabel)
          
          salelabel_serializer = self.fields['saleLabel']
          salelabel_instance = instance.saleLabel
          salelabel_serializer.update(salelabel_instance, salelabel)
          
          print(newlabel)
          return super().update(instance, validated_data)
     
class UpdateProductSerializer(serializers.ModelSerializer):
     # category = serializers.StringRelatedField(many=True)
     newLabel = NewLavelSerializer(required=False) #f
     saleLabel = SaleLavelSerializer(required=False) #f
     # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
     images = PictureSerializer(many=True, read_only=True) #m
     uploaded_images = serializers.ListField(
          child = serializers.ImageField(max_length = 1000000, allow_empty_file = False, use_url = False),
          write_only=True)
     sizes = SizeSerializer(many=True, required=False) #mt
     # ratings = RatingSerializer(many = True, required=False)
     # reviews = ReviewSerializer(many = True, required=False)
     # tags = serializers.StringRelatedField(many = True, required=False)
     # colors = serializers.StringRelatedField(many=True, required=False)
     
     class Meta:
          model = Product
          fields = '__all__'
          

     def create(self, validated_data):
          uploaded_images = validated_data.pop("uploaded_images")
          # newlabel_data = validated_data.pop('newLabel')
          # salelabel_data = validated_data.pop('saleLabel')
          # print(images_data)
          # newLabel, created = NewLabel.objects.get_or_create(**newlabel_data)
          # saleLabel, created = SaleLabel.objects.get_or_create(**salelabel_data)
          
          product = Product.objects.create(**validated_data)
          for imgae in uploaded_images:
               newproduct_image = Image.objects.create(product=product, picture=imgae)
               
          return product


class ProductImagePostSerializer(serializers.ModelSerializer):
     # category = serializers.StringRelatedField(many=True)
     # newLabel = NewLavelSerializer() #f
     # saleLabel = SaleLavelSerializer() #f
     # images = serializers.HyperlinkedRelatedField(many=True, view_name="product-detail", read_only=True, lookup_field="product-detail", )
     images = PictureSerializer(many=True, read_only=True) #m
     uploaded_images = serializers.ListField(
          child = serializers.ImageField(max_length = 1000000, allow_empty_file = False, use_url = False),
          write_only=True)
     # sizes = SizeSerializer(many=True, required=False) #mt
     # ratings = RatingSerializer(many = True, required=False)
     # reviews = ReviewSerializer(many = True, required=False)
     # tags = TagSerializer(many = True, required=False)
     # colors = ColorSerializer(many=True, required=False)
     
     class Meta:
          model = Product
          fields = '__all__'
          

     # def create(self, validated_data):
     #      uploaded_images = validated_data.pop("uploaded_images")
     #      for imgae in uploaded_images:
     #           newproduct_image = Image.objects.create(product=product, picture=imgae)
               
     #      return newproduct_image
     
     