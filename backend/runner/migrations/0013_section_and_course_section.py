from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0012_merge_20251203_1758"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Section",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("is_public", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_sections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Sections can be nested; parent cannot be deleted while children exist.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="children",
                        to="runner.section",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="section",
            index=models.Index(
                fields=["parent"], name="runner_section_parent_idx"
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="section",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional section to group courses; sections can be nested.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="runner.section",
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(
                fields=["section"], name="runner_course_section_idx"
            ),
        ),
    ]
