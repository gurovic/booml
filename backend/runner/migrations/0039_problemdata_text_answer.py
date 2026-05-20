from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0038_teacheraccessrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="problemdata",
            name="text_answer",
            field=models.TextField(blank=True, null=True),
        ),
    ]
