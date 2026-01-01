from ckeditor.fields import RichTextField
# from cloudinary.models import CloudinaryField
from django_countries.fields import CountryField
import uuid
from customers.models import Customer

from products.models import Product

from django.db import models
from suppliers.models import Supplier
from utils import random
from utils.models.common_fields import Timestamp
from django.utils.timezone import now
# from django.contrib.auth import get_user_model
# User = get_user_model()

def upload_to(instance, filename):
    return 'assets/uploads/order/images/{filename}'.format(filename=filename)

STATUS_CHOICE = (
     ('refunded', 'refunded'),
     ('cancelled', 'cancelled'),
     ('pending', 'pending'),
     ('completed', 'completed'),
     )


class Payment(models.Model):
     cardNumber    = models.CharField(max_length=100, blank=True, null=True)
     cardType = models.CharField(max_length=100, blank=True, null=True)

     name = models.CharField(max_length=100, blank=True, null=True)
     paymentTime = models.CharField(max_length=100, blank=True, null=True)
     
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("Payment")
          verbose_name_plural = ("Payments")

     def __str__(self):
          return self.cardNumber
     

class ShippingAddres(models.Model):
     fullAddress    = models.CharField(max_length=100, blank=True, null=True)
     phoneNumber = models.CharField(max_length=100, blank=True, null=True)

     name = models.CharField(max_length=100, blank=True, null=True)
     
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("ShippingAddres")
          verbose_name_plural = ("ShippingAddress")

     def __str__(self):
          return self.phoneNumber
     
     
class History(models.Model):
     completionTime    = models.DateTimeField(blank=True, null=True)
     deliveryTime = models.DateTimeField(blank=True, null=True)

     orderTime = models.DateTimeField(default=now, blank=True, null=True)
     paymentTime = models.DateTimeField(blank=True, null=True)
     
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("History")
          verbose_name_plural = ("Historys")
          
     

class Delivery(models.Model):
     name    = models.CharField(max_length=100, blank=True, null=True)
     shipBy = models.CharField(max_length=100, blank=True, null=True)

     speedy = models.CharField(max_length=100, blank=True, null=True)
     trackingNumber = models.CharField(max_length=100, blank=True, null=True)
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("Delivery")
          verbose_name_plural = ("Deliverys")

     def __str__(self):
          return self.name
     
     
class Order(models.Model):
     orderNumber = models.CharField(max_length=100, blank=True, null=True)
     name    = models.CharField(max_length=100, blank=True, null=True)
     customer = models.ForeignKey(Customer, related_name='customer', on_delete=models.CASCADE, blank=True, null=True)
     
     delivery = models.ForeignKey(Delivery, related_name='delivery', on_delete=models.CASCADE, blank=True, null=True)
     
     history = models.ForeignKey(History, related_name='history', on_delete=models.CASCADE, blank=True, null=True)
     
     payment = models.ForeignKey(Payment, related_name='payment', on_delete=models.CASCADE, blank=True, null=True)
     
     shippingAddress = models.ForeignKey(ShippingAddres, related_name='shippingAddress', on_delete=models.CASCADE, blank=True, null=True)
     
     shipping = models.IntegerField(default=0, blank=True, null=True)
     
     status = models.CharField(max_length=100, choices=STATUS_CHOICE, default="draft", blank=True, null=True)
     
     totalAmount = models.FloatField(default=0, blank=True, null=True)
     subTotal = models.FloatField(default=0, blank=True, null=True)
     taxes = models.FloatField(default=0, blank=True, null=True)
     discount = models.FloatField(default=0, blank=True, null=True)
     totalQuantity = models.IntegerField(default=0, blank=True, null=True)
     
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)

     class Meta:
          verbose_name = ("Order")
          verbose_name_plural = ("Orders")

     def __str__(self):
          return self.name
     
class Item(models.Model):
     order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, blank=True, null=True)
     product = models.ForeignKey(Product, related_name='items', on_delete=models.CASCADE, blank=True, null=True)
     coverUrl = models.ImageField(upload_to=upload_to, blank=True, null=True)
     name = models.CharField(max_length=100, default="", blank=True, null=True)
     sku = models.CharField(max_length=500, default="", blank=True, null=True)
     service = models.CharField(max_length=500, default="" ,blank=True, null=True)
     quantity = models.IntegerField(default=0, blank=True, null=True)
     price  = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
     total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
     code = models.IntegerField(default=0, blank=True, null=True)
     duration = models.IntegerField(default=0, blank=True, null=True)
     
     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     
     
     

class Timeline(models.Model):
     timeline = models.ForeignKey(History, related_name='timeline', on_delete=models.CASCADE, blank=True, null=True)
     
     title = models.CharField(max_length=100, blank=True, null=True)
     time   = models.DateTimeField(auto_now=True)
     createdAt  = models.DateTimeField(default=now, blank=True, null=True)
     

     class Meta:
          verbose_name = ("Timeline")
          verbose_name_plural = ("Timelines")

     def __str__(self):
          return self.title
     
     
