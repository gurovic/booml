# Generated migration to rename root sections and add last_activity_at

from django.db import migrations, models
from django.utils import timezone


RENAMES = {
    "Авторские": "Авторское",
    "Тематические": "Тематическое",
}


def rename_root_sections(apps, schema_editor):
    Section = apps.get_model("runner", "Section")
    for old_title, new_title in RENAMES.items():
        Section.objects.filter(title=old_title, parent__isnull=True).update(
            title=new_title
        )


def reverse_rename(apps, schema_editor):
    Section = apps.get_model("runner", "Section")
    for old_title, new_title in RENAMES.items():
        Section.objects.filter(title=new_title, parent__isnull=True).update(
            title=old_title
        )


def populate_last_activity(apps, schema_editor):
    CourseParticipant = apps.get_model("runner", "CourseParticipant")
    CourseParticipant.objects.filter(last_activity_at__isnull=True).update(
        last_activity_at=models.F("added_at")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0021_add_pinned_course"),
    ]

    operations = [
        migrations.AddField(
            model_name="courseparticipant",
            name="last_activity_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Last time user had activity in this course",
            ),
        ),
        migrations.RunPython(populate_last_activity, migrations.RunPython.noop),
        migrations.RunPython(rename_root_sections, reverse_rename),
    ]
