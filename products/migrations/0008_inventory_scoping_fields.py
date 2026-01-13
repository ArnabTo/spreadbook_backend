from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0002_companycustomization_prescription_flags"),
        ("products", "0007_product_category_ref_product_extra_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorycategory",
            name="companyId",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_categories",
                to="company.company",
            ),
        ),
        migrations.AddField(
            model_name="inventoryitem",
            name="companyId",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_items",
                to="company.company",
            ),
        ),
        migrations.AddField(
            model_name="inventoryitem",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inventory_items",
                to="company.branch",
            ),
        ),
        migrations.AlterField(
            model_name="inventoryitem",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="products.inventorycategory",
            ),
        ),
    ]
