from django.db import models
from ckeditor.fields import RichTextField
from authenticator.models import User
from django.utils.text import slugify
from django.db.models.signals import pre_save,post_save
from .utils import get_read_time
from django.urls import reverse
from taggit.managers import TaggableManager
from PIL import Image
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
     return 'assets/uploads/blog/{filename}'.format(filename=filename)


class Post(models.Model):
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
     author = models.ForeignKey(User, on_delete= models.CASCADE, blank=True, null=True)
     metaDescription = models.CharField(max_length=200, default="", blank=True, null=True)
     description = models.CharField(max_length=200, default="", blank=True, null=True)
     content = RichTextField(blank=True, null=True)
     likes = models.ManyToManyField(User, blank=True, related_name='post_likes')
     coverUrl = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     metaKeywords = models.CharField(max_length=200, default="", blank=True, null=True)
     publish  = models.CharField(max_length=100, choices=PUBLISH_CHOICE, default="published", blank=True, null=True)
     tags = TaggableManager(blank=True)
     totalViews = models.IntegerField(default=0, blank=True, null=True)
     totalShares = models.IntegerField(default=0, blank=True, null=True)
     totalComments = models.IntegerField(default=0, blank=True, null=True)
     totalFavorites = models.IntegerField(default=0, blank=True, null=True)
     
     createdAt = models.DateTimeField(default=now, blank=True, null=True)
     updatedAt = models.DateTimeField(auto_now=True)

     class Meta:
          ordering = ['-createdAt']

     def __str__(self):
          return self.title

     def save(self, *args, **kwargs):
          self.slug = slugify(self.title, allow_unicode=True)
          super().save(*args, **kwargs)

          for tag in self.tags.all():
               tag_dict,_ = TagDict.objects.get_or_create(tag=str(tag))
               tag_dict.count += 1
               tag_dict.save()

     def get_absolute_url(self):
          return reverse('post_detail', kwargs={"slug":self.slug})

     def get_like_url(self):
          return reverse('like-toggle', kwargs={"slug":self.slug})
     
     def get_api_like_url(self):
          return reverse('like-api-toggle', kwargs={"slug":self.slug})


def pre_save_post_receiver(sender, instance, *args, **kwargs):
     if instance.content:
          instance.read_time = get_read_time(instance.content)

pre_save.connect(pre_save_post_receiver, sender=Post)



class FavouritePost(models.Model):
     user = models.ForeignKey(User, on_delete=models.CASCADE)
     posts = models.ManyToManyField(Post)
     
     
class Comment(models.Model):
     # users = models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments', blank=True, null=True)
     post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments', blank=True, null=True)
     name = models.CharField(max_length=80, blank=True, null=True)
     avatarUrl = models.ImageField(null=True, blank=True, upload_to=upload_to_blog)
     message = models.CharField(max_length=200, default="", blank=True, null=True)
     postedAt = models.DateTimeField(auto_now_add=True)
     parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE, blank=True, related_name='replyComment')
     
     class Meta:
          ordering = ['-postedAt']

     def __str__(self):
          return 'Comment {} by {}'.format(self.message, self.name)