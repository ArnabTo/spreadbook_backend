from django.contrib.contenttypes import fields
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import timezone



class Calendar(models.Model):
     title = models.CharField(max_length=80, default="", blank=True, null=True)
     allDay = models.BooleanField(default=False, blank=True, null=True)
     color = models.CharField(max_length=80, default="", blank=True, null=True)
     description = models.CharField(max_length=500, default="", blank=True, null=True)
     start = models.IntegerField(default=0, blank=True, null=True)
     end = models.IntegerField(default=0, blank=True, null=True)


     class Meta:
          verbose_name = ("calendar")
          verbose_name_plural = ("calendars")

     def __str__(self):
          return self.title