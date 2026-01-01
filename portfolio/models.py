from django.db import models
from ckeditor.fields import RichTextField
from django.utils.text import slugify
from django.urls import reverse
from django.dispatch import receiver
from django.utils.timezone import now

# Create your models here.
class TagDict(models.Model):
     tag = models.CharField(max_length=100)
     count = models.IntegerField(default=0)

     def __str__(self):
          return self.tag

PUBLISH_CHOICE = (
    ('published', 'published'),
    ('draft', 'draft'),
    ('All', 'All'),
)


def upload_to_blog(instance, filename):
     return 'assets/uploads/portfolio/{filename}'.format(filename=filename)


class Portfolio(models.Model):
     CATEGORY_CHOICES = ( 
          ("kitchen cabinet", "kitchen cabinet"), 
          ("wall cabinet", "wall cabinet"), 
          ("Living", "Living"), 
          ("TV cabinet", "TV cabinet"), 
          ("CNC design", "CNC Design"), 
     ) 
     
     category = models.CharField( 
          max_length = 20, 
          choices = CATEGORY_CHOICES, 
          default = 'Living'
          ) 
     metaTitle = models.CharField(max_length=200, blank=True, null=True)
     title = models.CharField(max_length=200, blank=True, null=True)
     slug = models.SlugField(max_length=200, unique=True, blank=True, null=True)
     author = models.CharField(max_length=200, default = 'Royal Park', blank=True, null=True)
     metaDescription = models.CharField(max_length=200, default="", blank=True, null=True)
     description = models.CharField(max_length=200, default="", blank=True, null=True)
     content = RichTextField(blank=True, null=True)
     
     coverUrl = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     imga = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     imgb = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     imgc = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     imgd = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     imge = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     
     metaKeywords = models.CharField(max_length=200, default="", blank=True, null=True)
     publish  = models.CharField(max_length=100, choices=PUBLISH_CHOICE, default="published", blank=True, null=True)
     
     createdAt = models.DateTimeField(default=now, blank=True, null=True)
     updatedAt = models.DateTimeField(auto_now=True)

     class Meta:
          ordering = ['-createdAt']

     def save(self, *args, **kwargs):
          self.slug = slugify(self.title, allow_unicode=True)
          super().save(*args, **kwargs)






# class image(models.Model):
#      # users = models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments', blank=True, null=True)
#      post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments', blank=True, null=True)
#      name = models.CharField(max_length=80, blank=True, null=True)
#      avatarUrl = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
#      message = models.CharField(max_length=200, default="", blank=True, null=True)
#      postedAt = models.DateTimeField(auto_now_add=True)
#      parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE, blank=True, related_name='replyComment')
     
#      class Meta:
#           ordering = ['postedAt']

#      def __str__(self):
#           return 'Comment {} by {}'.format(self.message, self.name)
