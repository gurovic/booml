from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("runner", "0035_restore_problem_task_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="gpu_access",
            field=models.BooleanField(default=False, verbose_name="Доступ к GPU"),
        ),
    ]
