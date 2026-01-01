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
from django.db.models import Q

from .category_model import Category
from .unit_model import Unit


# lets us explicitly set upload path and filename
def upload_to(instance, filename):
    return "assets/uploads/product/images/{filename}".format(filename=filename)


def upload_to_multi(instance, filename):
    return "assets/uploads/product/images/multi{filename}".format(filename=filename)


def upload_to_barcode(instance, filename):
    return "assets/uploads/product/barcode/{filename}".format(filename=filename)


def upload_to_qrcode(instance, filename):
    return "assets/uploads/product/qrcode/{filename}".format(filename=filename)


GENDER_CHOICE = (
    ("Kids", "Kids"),
    ("Men", "Men"),
    ("Women", "Women"),
    ("All", "All"),
)

PUBLISH_CHOICE = (
    ("published", "published"),
    ("draft", "draft"),
    ("All", "All"),
)

CATEGORY_CHOICE = (
    ("Accessories", "Accessories"),
    ("Shose", "Shose"),
    ("Apparel", "Apparel"),
)

INVENTORY_CHOICE = (
    ("out of stock", "out of stock"),
    ("low stock", "low stock"),
    ("in stock", "in stock"),
)


class NewLabel(models.Model):
    # product  = models.ForeignKey(Product,related_name='newLabel', on_delete=models.CASCADE, null=True)
    enabled = models.BooleanField(default=False)
    content = models.CharField(max_length=100, default="New")

    def __str__(self):
        return f"{self.content}"


class SaleLabel(models.Model):
    # product  = models.ForeignKey(Product,related_name='saleLabel', on_delete=models.CASCADE, null=True)
    enabled = models.BooleanField(default=False)
    content = models.CharField(max_length=100, default="Sale")

    def __str__(self):
        return f"{self.content}"


class Size(models.Model):
    label = value = models.CharField(max_length=100, null=True, blank=True)
    value = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.label = self.value
        super(Size, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.label}"


class Product(Timestamp):
    """Product model for storing product data🛢"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Multi-tenant scoping (MegaShop/SaaS)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="products",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="products",
    )

    name = models.CharField(max_length=100, null=True, blank=True)
    # NOTE: code is unique per company (not globally) to support multi-tenant catalogs.
    code = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=100, default="", null=True, blank=True)

    gender = models.CharField(
        max_length=100, choices=GENDER_CHOICE, default="All", blank=True, null=True
    )
    publish = models.CharField(
        max_length=100,
        choices=PUBLISH_CHOICE,
        default="published",
        blank=True,
        null=True,
    )
    inventoryType = models.CharField(
        max_length=100,
        choices=INVENTORY_CHOICE,
        default="in stock",
        blank=True,
        null=True,
    )

    subDescription = models.CharField(max_length=500, blank=True, null=True)
    description = RichTextField(blank=True, null=True)
    # content = RichTextField(blank=False, null=False)
    available = models.IntegerField(default=0)

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, blank=True, null=True)
    # color = models.CharField(max_length=300, default="", blank=True, null=True)
    price = models.FloatField(default=0, blank=True, null=True)
    priceSale = models.FloatField(default=0, blank=True, null=True)
    regular_price = models.FloatField(default=0, blank=True, null=True)
    taxes = models.FloatField(default=0, blank=True, null=True)
    in_stock = models.IntegerField(default=0)
    is_publish = models.BooleanField(default=False)

    totalRatings = models.FloatField(default=0, blank=True, null=True)
    totalSold = models.IntegerField(default=0)
    totalPurchase = models.IntegerField(
        default=0,
        help_text="Cumulative purchased quantity added to stock (auto-incremented when receiving/purchasing).",
    )
    totalReviews = models.FloatField(default=0, blank=True, null=True)

    # img = models.ManyToManyField(Picture, related_name='img', blank=True, null=True)

    image = models.ImageField(upload_to=upload_to, blank=True, null=True)
    coverUrl = models.ImageField(upload_to=upload_to, blank=True, null=True)
    barcode = models.ImageField(upload_to=upload_to_barcode, blank=True, null=True)
    qrcode = models.ImageField(upload_to=upload_to_qrcode, blank=True, null=True)

    quantity = models.IntegerField(default=0)
    out_of_stock = models.BooleanField(default=False)

    newLabel = models.ForeignKey(
        NewLabel,
        related_name="newLabel",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    saleLabel = models.ForeignKey(
        SaleLabel,
        related_name="saleLabel",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    sizes = models.ManyToManyField(Size, related_name="products", blank=True)

    # ratings = models.ManyToManyField(Rating, related_name='ratings', blank=True)
    mfg_date = models.DateField(
        help_text="The MFG date is the date the product was manufactured, or the Manufacturing Date (MFG). It is not an expiration date.",
        null=True,
        blank=True,
    )
    exp_date = models.DateField(
        help_text="An expiration date is the last day that a consumable product such as food or medicine.",
        null=True,
        blank=True,
    )

    # Pharmacy / Rx fields (optional; UI-safe)
    prescription_required = models.BooleanField(
        default=False,
        help_text="True if sale requires an approved prescription (when enforcement is enabled).",
    )
    controlled_substance = models.BooleanField(
        default=False,
        help_text="True if item is controlled/regulated.",
    )
    dosage_form = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Tablet, Capsule, Syrup, Injection, Ointment, etc.",
    )
    strength = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Strength/dose, e.g. 500mg, 5mg/5ml, etc.",
    )
    mrp = models.FloatField(
        default=0,
        blank=True,
        null=True,
        help_text="Maximum Retail Price (MRP).",
    )
    status = models.CharField(
        max_length=20,
        choices=[("out of stock", "Out of Stock"), ("in stock", "In Stock")],
        default="In stock",
    )
    technology = models.CharField(
        verbose_name="Technology",
        max_length=40,
        help_text="Bluetooth, Wi-Fi, USB, Ethernet, etc.",
        null=True,
        blank=True,
    )
    uses_for_product = models.CharField(
        verbose_name="Specific Uses For Product",
        max_length=50,
        help_text="Personal, Gaming, Business, etc.",
        null=True,
        blank=True,
    )
    brand_name = models.CharField(
        verbose_name="Brand Name",
        max_length=50,
        help_text="Example: Apple, Samsung, Sony, LG, etc.",
        null=True,
        blank=True,
    )
    manufacturer = models.CharField(
        verbose_name="Manufacturer",
        max_length=50,
        help_text="Example: Apple, Samsung, LG, Sony, etc.",
        null=True,
        blank=True,
    )
    size = models.CharField(
        verbose_name="Size",
        max_length=100,
        default=0,
        help_text="The numeric or text version of the item's size. Example: Small, Medium, Large, X-Large, XX-Large, etc.",
        null=True,
        blank=True,
    )
    weight = models.CharField(
        verbose_name="Weight",
        max_length=10,
        help_text="The numeric or text version of the item's weight. Example: 1.5 lbs, 2.5 lbs, etc.",
        null=True,
        blank=True,
    )
    height = models.CharField(
        verbose_name="Height",
        max_length=10,
        help_text="The numeric or text version of the item's height. Example: 1.5 inches, 2.5 inches, etc.",
        null=True,
        blank=True,
    )
    color = models.CharField(
        verbose_name="Color",
        max_length=200,
        default="#0000",
        help_text="The color of the item. Example: Red, Blue, Green, etc.",
        null=True,
        blank=True,
    )
    shape = models.CharField(
        verbose_name="Shape",
        max_length=10,
        help_text="The shape of the item. Example: Round, Square, Oval, etc.",
        null=True,
        blank=True,
    )
    material_type = models.CharField(
        verbose_name="Material Type",
        max_length=10,
        help_text="what material is the product made out of? '\n Example: plastic, metal, wood, etc.",
        null=True,
        blank=True,
    )
    count_sold = models.IntegerField(default=0)
    country = models.CharField(
        verbose_name="Country",
        max_length=10,
        help_text="Country? '\n Example: BD, China, etc.",
        null=True,
        blank=True,
    )
    recently_sold = models.DateTimeField(null=True, blank=True)
    recently_added = models.DateTimeField(null=True, blank=True)
    recently_viewed = models.DateTimeField(null=True, blank=True)
    recently_updated = models.DateTimeField(null=True, blank=True)
    supplier_price = models.FloatField(default=0, blank=True, null=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, blank=True, null=True
    )
    createdAt = models.DateTimeField(default=now, blank=True, null=True)
    updateAt = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """override the save method for logical purposes"""
        if self.in_stock >= 21:
            self.status = "in stock"
            self.inventoryType = "in stock"
            self.available = self.in_stock
            self.out_of_stock = False

        elif self.in_stock >= 1 | self.in_stock <= 20:
            self.status = "in stock"
            self.inventoryType = "low stock"
            self.available = self.in_stock
            self.out_of_stock = False

        else:
            self.status = "out of stock"
            self.inventoryType = "out of stock"
            # if out of stock, set out_of_stock flag to True
            self.out_of_stock = True
            self.available = self.in_stock
        # Save the product with a random product code.
        # self.code = self.code + 1
        super(Product, self).save(*args, **kwargs)

    def save_model(self, request, obj, form, change):
        # Only set user during the first save.
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def __str__(self):
        """String for representing the Model object."""
        return f"{self.name}"

    class Meta:
        indexes = [
            models.Index(fields=["companyId", "code"], name="idx_product_company_code"),
            models.Index(fields=["companyId", "name"], name="idx_product_company_name"),
            models.Index(fields=["companyId", "sku"], name="idx_product_company_sku"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["companyId", "code"],
                condition=Q(code__isnull=False) & ~Q(code=""),
                name="uniq_product_company_code",
            ),
        ]


# price = models.FloatField(default=0, blank=True, null=True)
#     priceSale = models.FloatField(default=0, blank=True, null=True)
#     regular_price = models.FloatField(default=0, blank=True, null=True)
#     taxes = models.FloatField(default=0, blank=True, null=True)
#     in_stock = models.IntegerField(default=0)
#     is_publish  = models.BooleanField(default=False)

#     totalRatings = models.FloatField(default=0, blank=True, null=True)
#     totalSold = models.IntegerField(default=0)
#     totalReviews  = models.FloatField(default=0, blank=True, null=True)
# class Size(models.Model):
#     product  = models.ForeignKey(Product,related_name='sizes', on_delete=models.CASCADE, null=True)
#     content  = models.CharField(max_length=100)

#     def __str__(self):
#         return f'{self.content}'


class Image(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE, null=True
    )
    picture = models.ImageField(upload_to=upload_to_multi, null=True, blank=True)


class Tag(models.Model):
    product = models.ForeignKey(
        Product, related_name="tags", on_delete=models.CASCADE, null=True
    )
    content = models.CharField(max_length=100)

    def __str__(self):
        return self.content


class Color(models.Model):
    label = value = models.CharField(max_length=100, null=True, blank=True)
    value = models.CharField(max_length=100, null=True, blank=True)

    # def save(self, *args, **kwargs):
    #     self.label = self.value
    #     super(Color, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.label}"
