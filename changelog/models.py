from django.db import models
from ckeditor.fields import RichTextField
from authenticator.models import User
from django.utils.text import slugify
from django.db.models.signals import pre_save,post_save
from django.dispatch import receiver
from django.utils.timezone import now
import uuid
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
User = get_user_model()


def upload_to_changelog(instance, filename):
    return 'assets/uploads/changelog/%Y/%m/{filename}'.format(filename=filename)

class Changelog(models.Model):
     creator = models.ForeignKey(User,on_delete=models.CASCADE,related_name='changelog', blank=True, null=True)
     company_id = models.CharField(max_length=100, null=True, blank=True)
     company = models.CharField(max_length=100, null=True, blank=True)      

     name = models.CharField(
          verbose_name=_('Update Name'),
          max_length=50,
          blank=True, null=True
     )
     is_read = models.BooleanField(
          default=False,
          help_text=_(
               'User reads the updates'
          ),
     )
     description = models.TextField(blank=True, null=True, verbose_name=_('Updates Decription'))
     
     image = models.ImageField(upload_to=upload_to_changelog, blank=True, null=True)
     
     createdAt = models.DateTimeField(default=now, blank=True, null=True)
     updatedAt = models.DateTimeField(auto_now=True)