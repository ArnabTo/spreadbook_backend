from ckeditor.fields import RichTextField
# from cloudinary.models import CloudinaryField
from django_countries.fields import CountryField
import uuid

from django.db import models
from suppliers.models import Supplier
from utils import random
from utils.models.common_fields import Timestamp
from django.utils.timezone import now
from .product_model import Product



class Rating(models.Model):
     id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     product  = models.ForeignKey(Product,related_name='ratings', on_delete=models.CASCADE, null=True) 
     name    = models.CharField(max_length=100, blank=True, null=True)
     starCount = models.IntegerField(default=0, blank=True, null=True)
     reviewCount = models.IntegerField(default=0, blank=True, null=True)
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("Rating")
          verbose_name_plural = ("Ratings")

     def __str__(self):
          return self.name

     def get_absolute_url(self):
          return reverse("Rating_detail", kwargs={"pk": self.pk})
     