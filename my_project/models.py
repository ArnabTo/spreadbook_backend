from django.db import models
from ckeditor.fields import RichTextField
from authenticator.models import User
from django.utils.text import slugify
from django.db.models.signals import pre_save,post_save
from django.urls import reverse
from taggit.managers import TaggableManager
from PIL import Image
from django.dispatch import receiver
from django.utils.timezone import now


PUBLISH_CHOICE = (
    ('published', 'published'),
    ('draft', 'draft'),
    ('All', 'All'),
)

STATUS_CHOICE = (
    ('completed', 'completed'),
    ('ongoing', 'ongoing'),
    ('signed', 'signed'),
    ('draft', 'draft'),
    ('all', 'all'),
)


def upload_to_project(instance, filename):
     return 'assets/uploads/project/{filename}'.format(filename=filename)


class Project(models.Model):
     CATEGORY_CHOICES = ( 
          ("1", "Programming/Technology"), 
          ("2", "Health/Fitness"), 
          ("3", "Personal"), 
          ("4", "Fashion"), 
          ("5", "Food"), 
          ("6", "Travel"), 
          ("7", "Business"), 
          ("8", "Art"),
          ("9", "Other"), 
     ) 
     
     category = models.CharField( 
          max_length = 20, 
          choices = CATEGORY_CHOICES, 
          default = '1'
          ) 
     metaTitle = models.CharField(max_length=200, blank=True, null=True)
     title = models.CharField(max_length=200, blank=True, null=True)
     slug = models.SlugField(max_length=200, unique=True, blank=True, null=True)
     description = models.CharField(max_length=200, default="", blank=True, null=True)
     content = RichTextField(blank=True, null=True)
     
     coverUrl = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     imgUrla = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     imgUrlb = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     imgUrlc = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     imgUrld = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     imgUrle = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     imgUrlf = models.ImageField(null=True, blank=True, upload_to=upload_to_project)
     
     publish  = models.CharField(max_length=100, choices=PUBLISH_CHOICE, default="published", blank=True, null=True)
     status  = models.CharField(max_length=100, choices=STATUS_CHOICE, default="draft", blank=True, null=True)
     
     
     createdAt = models.DateTimeField(default=now, blank=True, null=True)
     updatedAt = models.DateTimeField(auto_now=True)

     class Meta:
          ordering = ['-createdAt']

     def __str__(self):
          return self.title

     def save(self, *args, **kwargs):
          self.slug = slugify(self.title, allow_unicode=True)
          super().save(*args, **kwargs)


     def get_absolute_url(self):
          return reverse('post_detail', kwargs={"slug":self.slug})

     def get_like_url(self):
          return reverse('like-toggle', kwargs={"slug":self.slug})
     
     def get_api_like_url(self):
          return reverse('like-api-toggle', kwargs={"slug":self.slug})


