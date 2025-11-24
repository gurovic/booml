from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0002_problem_author_problem_is_published"),
    ]

    operations = [
        migrations.AddField(
            model_name="problemdescriptor",
            name="metric_code",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="problemdescriptor",
            name="metric_name",
            field=models.CharField(default="rmse", max_length=100),
        ),
    ]
