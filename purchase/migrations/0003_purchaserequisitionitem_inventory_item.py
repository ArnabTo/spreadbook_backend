from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
        ("purchase", "0002_purchaserequisition_purchaserequisitionitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaserequisitionitem",
            name="inventory_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="products.inventoryitem",
            ),
        ),
    ]
