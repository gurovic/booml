from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ("runner", "0009_remove_contest_courses_contest_course_contest_status_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Optional parent course to build hierarchies (e.g., sections/years). "
                    "Parent cannot be deleted while children exist."
                ),
                null=True,
                on_delete=models.PROTECT,
                related_name="children",
                to="runner.course",
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["parent"], name="runner_course_parent_idx"),
        ),
    ]
