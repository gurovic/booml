from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0013_contest_access_type_access_token_allowed_participants"),
        ("runner", "0013_section_and_course_section"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="course",
            name="parent",
        ),
        migrations.AlterField(
            model_name="course",
            name="section",
            field=models.ForeignKey(
                blank=True,
                help_text="Section that owns the course; sections can be nested.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="runner.section",
            ),
        ),
        migrations.AddConstraint(
            model_name="section",
            constraint=models.UniqueConstraint(
                condition=models.Q(parent__isnull=True),
                fields=("title",),
                name="runner_unique_root_section_title",
            ),
        ),
    ]
