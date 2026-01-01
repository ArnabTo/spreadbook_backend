from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from utils.models.common_fields import Timestamp
import uuid
from django.utils.timezone import now 
from products.models.product_model import Product
from customers.models import Customer

from django.contrib.auth import get_user_model
User = get_user_model()
from authenticator.models import User as Genuser, PayrollOption



class Performance(models.Model):
     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     creator     = models.ForeignKey(User,on_delete=models.SET_NULL,related_name='perform_user', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)

     product = models.ForeignKey(Product,on_delete=models.SET_NULL,related_name='perform_product', blank=True, null=True)
     customer = models.ForeignKey(Customer,on_delete=models.SET_NULL,related_name='perform_customer', blank=True, null=True)
     reference = models.CharField(max_length=100, null=True, blank=True)
     
     purpose= models.CharField(max_length=100, null=True, blank=True)
     description = models.TextField(null=True, blank=True)
     amount = models.FloatField(default=0)
     
     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
