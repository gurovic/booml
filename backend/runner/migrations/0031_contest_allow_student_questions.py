from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0030_contestnotification_contestnotificationrecipient_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="allow_student_questions",
            field=models.BooleanField(
                default=True,
                help_text="Allow students to ask questions in contest notifications",
            ),
        ),
    ]
