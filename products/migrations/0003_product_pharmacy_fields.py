from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_inventoryitem_tracking_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="prescription_required",
            field=models.BooleanField(
                default=False,
                help_text="True if sale requires an approved prescription (when enforcement is enabled).",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="controlled_substance",
            field=models.BooleanField(
                default=False,
                help_text="True if item is controlled/regulated.",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="dosage_form",
            field=models.CharField(
                blank=True,
                help_text="Tablet, Capsule, Syrup, Injection, Ointment, etc.",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="strength",
            field=models.CharField(
                blank=True,
                help_text="Strength/dose, e.g. 500mg, 5mg/5ml, etc.",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="mrp",
            field=models.FloatField(
                blank=True,
                default=0,
                help_text="Maximum Retail Price (MRP).",
                null=True,
            ),
        ),
    ]
