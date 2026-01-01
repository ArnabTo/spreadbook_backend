import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacy", "0001_initial"),
        ("sales", "0007_alter_sale_is_return"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="prescription",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sales",
                to="pharmacy.prescription",
            ),
        ),
    ]
