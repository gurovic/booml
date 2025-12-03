from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('runner', '0005_merge_20251125_0803'),
        ('runner', '0005_course_courseparticipant'),  # файл которого нет, но Django его ждёт
    ]

    operations = []
