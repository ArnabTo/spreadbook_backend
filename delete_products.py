#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ERP_Shop.settings")
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from products.models import Product

print(f"Products before deletion: {Product.objects.count()}")
deleted, details = Product.objects.all().delete()
print(f"Deleted {deleted} objects")
print(f"Products after deletion: {Product.objects.count()}")
print("Details:", details)
