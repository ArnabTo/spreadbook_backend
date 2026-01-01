from rest_framework import serializers
from .models import Post, Comment

class CommentSerializer(serializers.ModelSerializer):
     class Meta:
          model = Comment
          fields = '__all__'
          
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)



class BlogSerializer(serializers.ModelSerializer):
     comments = CommentSerializer(many=True, required=False)
     class Meta:
          model = Post
          fields = '__all__'
          lookup_field = 'slug'
          extra_kwargs = {
               'url': {'lookup_field': 'slug'},
               'comments': {'required': False},
          }
     def create(self, validated_data):
          return super().create(validated_data)
     
     def update(self, instance, validated_data):
          return super().update(instance, validated_data)