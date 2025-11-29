from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0010_course_parent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional parent course to build hierarchies (e.g., sections/years). Parent cannot be deleted while children exist.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="runner.course",
            ),
        ),
    ]
