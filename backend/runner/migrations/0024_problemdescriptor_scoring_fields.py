from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0023_section_teachers"),
    ]

    operations = [
        migrations.AddField(
            model_name="problemdescriptor",
            name="score_curve_p",
            field=models.FloatField(
                blank=True,
                help_text="Curve coefficient for nonlinear score mapping (higher -> faster growth far from ideal).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="problemdescriptor",
            name="score_direction",
            field=models.CharField(
                blank=True,
                choices=[("maximize", "Maximize"), ("minimize", "Minimize")],
                default="",
                help_text="Optional manual scoring direction for custom metrics.",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="problemdescriptor",
            name="score_ideal_metric",
            field=models.FloatField(
                blank=True,
                help_text="Optional manual ideal raw metric value for custom metrics.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="problemdescriptor",
            name="score_reference_metric",
            field=models.FloatField(
                blank=True,
                help_text="Cached raw metric of sample submission used as nonlinear reference.",
                null=True,
            ),
        ),
    ]
