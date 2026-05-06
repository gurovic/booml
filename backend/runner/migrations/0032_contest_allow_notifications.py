from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0031_contest_allow_student_questions"),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="allow_notifications",
            field=models.BooleanField(
                default=True,
                help_text="Enable announcements and question/answer notifications for the contest",
            ),
        ),
    ]
