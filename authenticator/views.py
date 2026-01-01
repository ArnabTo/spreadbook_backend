from ast import If
from .models import UserDetails, CurrentStatusOfFields
from .serializers import UserCreateSerializer
from rest_framework import permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers, viewsets, permissions
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated 



class UserDetailsView(viewsets.ModelViewSet):
     queryset = UserDetails.objects.order_by('-creator_id')
     serializer_class = UserCreateSerializer
     parser_classes = (MultiPartParser, FormParser)
     
     authentication_classes = [TokenAuthentication]
     permission_classes = [IsAuthenticated]
     
     
     def get_queryset(self):
          creator = self.request.user
          user = self.request.user
          
          # print(Field.objects.filter(user=user).count())
          # if UserDetails.objects.count() is 10:
          #      print("hello")
          return UserDetails.objects.filter(creator=creator)

     def perform_create(self, serializer):
          serializer.save(creator=self.request.user)
          
     # # #Update
     def perform_update(self, serializer):
          creator = self.request.user
          userid = str(creator.id)
          lookup_field = 'pk'
          serializer.save(creator=self.request.user)