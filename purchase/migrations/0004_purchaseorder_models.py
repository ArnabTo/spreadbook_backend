from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
        ("suppliers", "0001_initial"),
        ("purchase", "0003_purchaserequisitionitem_inventory_item"),
    ]

    operations = [
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "po_number",
                    models.CharField(editable=False, max_length=32, unique=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("delivered", "Delivered"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("order_date", models.DateField(default=django.utils.timezone.now)),
                ("expected_delivery_date", models.DateField(blank=True, null=True)),
                (
                    "total_amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                ("created_by", models.CharField(blank=True, max_length=150, null=True)),
                (
                    "requisition",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="purchase_orders",
                        to="purchase.purchaserequisition",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="suppliers.supplier",
                    ),
                ),
            ],
            options={},
        ),
        migrations.CreateModel(
            name="PurchaseOrderItem",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=10)),
                ("unit", models.CharField(max_length=50)),
                (
                    "unit_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                (
                    "total_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                ("expiry_date", models.DateField(blank=True, null=True)),
                ("warranty_expiry_date", models.DateField(blank=True, null=True)),
                (
                    "inventory_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="products.inventoryitem",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="products.product",
                    ),
                ),
                (
                    "purchase_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="purchase.purchaseorder",
                    ),
                ),
            ],
            options={},
        ),
    ]
