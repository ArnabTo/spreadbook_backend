from django.contrib import admin
from .models import Post, FavouritePost, Comment, TagDict

# Register your models here.
admin.site.register(Post)
admin.site.register(FavouritePost)
admin.site.register(Comment)
admin.site.register(TagDict)