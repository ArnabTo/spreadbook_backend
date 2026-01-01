from django.db import models
from django.utils.timezone import now
from django.contrib.auth import get_user_model
User = get_user_model()
# from .product_model import Product

PAYMENT_CHOICE = (
     ('cash', 'cash'),
     ('bKash', 'bKash'),
     ('উপায় (upay)', 'উপায় (upay)'),
     ('nagad', 'nagad'),
     ('bank', 'bank'),
     )



class Billing(models.Model):
     invoiceNumber = models.CharField(max_length=100, null=True, blank=True)
     creator     = models.ForeignKey(User,on_delete=models.CASCADE,related_name='owner_billing', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)
     amount = models.CharField(max_length=100, null=True, blank=True)
     
     account_no = models.CharField(max_length=100, null=True, blank=True)
     transection_id  = models.CharField(max_length=100, null=True, blank=True)
     
     payment_method = models.CharField(max_length=100, choices= PAYMENT_CHOICE, default="", blank=True, null=True)

     description = models.TextField(null=True, blank=True)
     name = models.CharField(max_length=50, null=True, blank=True)
     is_paid = models.BooleanField(default=True, null=True, blank=True)
     
     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     

     def __str__(self):
          """String for representing the Model object."""
          return self.name
     
class BillingAddress(models.Model):
     creator     = models.ForeignKey(User,on_delete=models.CASCADE,related_name='owner_billing_address', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)
     
     name = models.CharField(max_length=50, null=True, blank=True)
     is_active = models.BooleanField(default=True, null=True, blank=True)
     

     def __str__(self):
          """String for representing the Model object."""
          return self.name