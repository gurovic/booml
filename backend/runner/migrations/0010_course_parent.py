from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0009_remove_contest_courses_contest_course_contest_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional parent course to build hierarchies (e.g., sections/years).",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="runner.course",
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["parent"], name="runner_course_parent_idx"
            ),
        ),
    ]
