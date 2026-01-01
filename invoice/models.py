from ckeditor.fields import RichTextField
# from cloudinary.models import CloudinaryField
from django_countries.fields import CountryField
import uuid

from django.db import models
from suppliers.models import Supplier
from utils import random
from utils.models.common_fields import Timestamp
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.dispatch import receiver


STATUS_CHOICE = (
    ('draft', 'draft'),
    ('paid', 'paid'),
    ('pending', 'pending'),
    ('overdue', 'overdue'),
)

class Invoice(Timestamp):
     invoiceNumber = models.CharField(max_length=100, null=True, blank=True)
     taxes = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
     shipping = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
     status = models.CharField(max_length=100, choices=STATUS_CHOICE, default="draft", blank=True, null=True)
     discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
     totalAmount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
     # invoiceCreator = 
     # invoiceFrom
     
     # invoiceTo
     
     # items
     
     dueDate   = models.DateTimeField(blank=True, null=True)
     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
