from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="companycustomization",
            name="enforce_prescriptions",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If enabled, prescription-required products cannot be sold unless an approved prescription is attached."
                ),
            ),
        ),
        migrations.AddField(
            model_name="companycustomization",
            name="enforce_controlled_substances",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If enabled, controlled substances additionally require an approved prescription."
                ),
            ),
        ),
    ]
