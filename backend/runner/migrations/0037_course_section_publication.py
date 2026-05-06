from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0036_profile_gpu_access"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="is_published",
            field=models.BooleanField(
                default=True,
                help_text="Visible to students when True; drafts are visible only to teachers.",
            ),
        ),
        migrations.AddField(
            model_name="section",
            name="is_published",
            field=models.BooleanField(
                default=True,
                help_text="Visible to students when True; drafts are visible only to teachers.",
            ),
        ),
    ]
