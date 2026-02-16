from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("runner", "0022_favorites_and_site_updates"),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionTeacher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                (
                    "section",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="section_teachers",
                        to="runner.section",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="section_teacher_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={},
        ),
        migrations.AlterUniqueTogether(
            name="sectionteacher",
            unique_together={("section", "user")},
        ),
        migrations.AddIndex(
            model_name="sectionteacher",
            index=models.Index(fields=["section", "user"], name="runner_secteacher_secusr_idx"),
        ),
        migrations.AddIndex(
            model_name="sectionteacher",
            index=models.Index(fields=["user", "section"], name="runner_secteacher_usrsec_idx"),
        ),
    ]

