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

def upload_to(instance, filename):
    return 'assets/uploads/review/images/{filename}'.format(filename=filename)


class Review(models.Model):
     id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     product  = models.ForeignKey(Product,related_name='reviews', on_delete=models.CASCADE, null=True) 
     name    = models.CharField(max_length=100, blank=True, null=True)
     email   = models.CharField(max_length=100, blank=True, null=True)
     comment = models.CharField(max_length=100, blank=True, null=True)
     isPurchased = models.BooleanField(default=False, blank=True, null=True)
     rating = models.FloatField(blank=True, null=True)
     
     avatarUrl = models.ImageField(upload_to=upload_to, blank=True, null=True)
     helpful = models.IntegerField(default=0, blank=True, null=True)
     attachments = models.FileField(blank=True, null=True)
     postedAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("Review")
          verbose_name_plural = ("Reviews")

     def __str__(self):
          return self.name

     def get_absolute_url(self):
          return reverse("Review_detail", kwargs={"pk": self.pk})

