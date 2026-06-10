from customers.models import Customer
from django.db import models
from django.db.models import Q
from utils.models.common_fields import Timestamp
from ckeditor.fields import RichTextField
from django.utils.text import slugify
import uuid
from django.utils.timezone import now


PUBLISH_CHOICE = (
    ('published', 'published'),
    ('draft', 'draft'),
    ('All', 'All'),
)


def upload_to_blog(instance, filename):
     return 'assets/uploads/service/{filename}'.format(filename=filename)

class ServiceItem(Timestamp):
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
     
     metaKeywords = models.CharField(max_length=200, default="", blank=True, null=True)
     publish  = models.CharField(max_length=100, choices=PUBLISH_CHOICE, default="published", blank=True, null=True)
     
     createdAt = models.DateTimeField(default=now, blank=True, null=True)
     updatedAt = models.DateTimeField(auto_now=True)

     class Meta:
          ordering = ['-createdAt']

     def save(self, *args, **kwargs):
          self.slug = slugify(self.title, allow_unicode=True)
          super().save(*args, **kwargs)

class Service(Timestamp):
     uuid          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     service_name = models.CharField(max_length=100)
     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
     net_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
     grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
     total_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
     charge = models.DecimalField(max_digits=10, decimal_places=2)
     description = models.TextField(blank=True, null=True)
     vat = models.DecimalField(max_digits=10, decimal_places=2, default=2.00, null=True, blank=True)
     paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

     class Meta:
          '''
          Meta class for the Service model.
          '''
          verbose_name = 'Service'
          verbose_name_plural = 'Services'

     def __str__(self):
          '''
          Return a string representation of the model object.
          '''
          return self.service_name

     def save(self, *args, **kwargs):
          '''
          Override the save method to calculate the total amount.
          '''
          self.grand_total = self.net_total + self.total_tax
          self.grand_total - self.vat + self.charge
          self.paid_amount = self.grand_total - self.charge
          super(Service, self).save(*args, **kwargs)


class ProductService(Timestamp):
    """Product Service catalog item — company-scoped, similar to Product but for services."""

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="product_services",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, db_index=True)
    arabic_name = models.CharField(max_length=200, blank=True, null=True)
    category = models.ForeignKey(
        "products.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_services",
    )
    is_tax_applied = models.BooleanField(default=False)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, null=True)
    sales_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quality_applicable = models.BooleanField(default=False)
    minimum_sales_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    avg_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    createdAt = models.DateTimeField(default=now, blank=True, null=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uniq_productservice_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "name"], name="idx_ps_company_name"),
            models.Index(fields=["company", "category"], name="idx_ps_company_category"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
