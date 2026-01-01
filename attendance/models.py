from decimal import Decimal

from django.db.models.signals import pre_save,post_save
from django.dispatch import receiver
from customers.models import Customer
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from products.models import Product
from utils import random
from utils.models.common_fields import Timestamp
from customers.models import Customer
import uuid
from datetime import datetime
from django.utils.timezone import now
from django.contrib.auth import get_user_model
User = get_user_model()


STATUS_CHOICE = (
     ('in', 'in'),
     ('out', 'out'), 
     ('break', 'break'),
     ('overtime', 'overtime'),
     )

class Attendance(models.Model):
     """ Sale model for storing sale data🛢 """
     id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     creator     = models.ForeignKey(User,on_delete=models.CASCADE,related_name='owner_attendance', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)
     
     person = models.ForeignKey(User,on_delete=models.CASCADE,related_name='attendance', blank=True, null=True)
     # Status
     is_present = models.BooleanField(default=False)
     time_in = models.DateTimeField(blank=True, null=True)
     time_out = models.DateTimeField(blank=True, null=True)
     
     count_hrs = models.FloatField(default=0, blank=True, null=True)
     overtime_hrs = models.FloatField(default=0, blank=True, null=True)
     break_hrs = models.FloatField(default=0, blank=True, null=True)
     
     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     
     
     # def save(self, *args, **kwargs):
     #      time_difference =   (self.time_out - self.time_in)
     #      hours_difference = time_difference.total_seconds() / 3600
     #      # print(hours_difference)
     #      self.count_hrs = hours_difference
     #      super().save(*args, **kwargs)

class AttendanceData(models.Model):
     attendance_data = models.ForeignKey(Attendance, related_name='attendance_data', on_delete=models.CASCADE, blank=True, null=True)
     status = models.CharField(max_length=100, choices=STATUS_CHOICE, default="", blank=True, null=True)
     is_present = models.BooleanField(default=False)
     
     count_hrs = models.FloatField(default=0, blank=True, null=True)
     break_hrs = models.FloatField(default=0, blank=True, null=True)

     updateAt   = models.DateTimeField(auto_now=True)
     createDate     = models.DateTimeField(default=now, blank=True, null=True)
     
