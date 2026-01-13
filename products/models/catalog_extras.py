import uuid

from django.db import models
from django.db.models import Q


class ProductType(models.Model):
    """User-manageable product/item type (Pharmacy, Fresh, Grocery, Bakery, Plastic, Fruits, etc)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="product_types",
    )

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=120, db_index=True)
    is_active = models.BooleanField(default=True)

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["companyId", "slug"], name="idx_pt_company_slug"),
            models.Index(fields=["companyId", "name"], name="idx_pt_company_name"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["companyId", "slug"],
                condition=Q(slug__isnull=False) & ~Q(slug=""),
                name="uniq_pt_company_slug",
            )
        ]

    def __str__(self) -> str:
        return self.name


class GenericName(models.Model):
    """Pharmacy generic name (e.g., Paracetamol, Omeprazole)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="generic_names",
    )

    name = models.CharField(max_length=150, db_index=True)
    is_active = models.BooleanField(default=True)

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["companyId", "name"], name="idx_gn_company_name"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["companyId", "name"],
                condition=Q(name__isnull=False) & ~Q(name=""),
                name="uniq_gn_company_name",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Brand(models.Model):
    """Optional brand registry (keeps existing Product.brand_name field intact)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    companyId = models.ForeignKey(
        "company.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="brands",
    )

    name = models.CharField(max_length=120, db_index=True)
    is_active = models.BooleanField(default=True)

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["companyId", "name"], name="idx_brand_company_name"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["companyId", "name"],
                condition=Q(name__isnull=False) & ~Q(name=""),
                name="uniq_brand_company_name",
            )
        ]

    def __str__(self) -> str:
        return self.name


class ProductBarcode(models.Model):
    """Multiple barcodes per product (EAN/UPC/etc)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="barcodes",
    )

    code = models.CharField(max_length=64, db_index=True)
    is_primary = models.BooleanField(default=False)

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "code"], name="uniq_product_barcode"
            ),
        ]

    def __str__(self) -> str:
        return self.code


class ProductBatch(models.Model):
    """Batch/lot tracking (best for Pharmacy + perishable items)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="batches",
    )
    branch = models.ForeignKey(
        "company.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="product_batches",
    )

    batch_no = models.CharField(max_length=60)
    mfg_date = models.DateField(null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)

    qty_on_hand = models.IntegerField(default=0)
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_batches",
    )

    receivedAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["product", "branch"], name="idx_batch_product_branch"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "branch", "batch_no"],
                condition=Q(batch_no__isnull=False) & ~Q(batch_no=""),
                name="uniq_batch_product_branch_no",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_id} - {self.batch_no}"
