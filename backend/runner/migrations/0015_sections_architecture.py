from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


ROOT_SECTION_TITLES = ("Авторские", "Тематические", "Олимпиады")


def _get_owner(apps):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    owner = User.objects.filter(is_superuser=True).order_by("id").first()
    if owner is None:
        owner = User.objects.order_by("id").first()
    if owner is None:
        owner = User.objects.create(username="system", is_staff=True, is_superuser=True)
        if hasattr(owner, "set_unusable_password"):
            owner.set_unusable_password()
            owner.save(update_fields=["password"])
        elif hasattr(owner, "password"):
            owner.password = "!"
            owner.save(update_fields=["password"])
    return owner


def create_root_sections(apps, schema_editor):
    Section = apps.get_model("runner", "Section")
    Course = apps.get_model("runner", "Course")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    owner = _get_owner(apps)
    roots = {}
    for title in ROOT_SECTION_TITLES:
        section, _created = Section.objects.get_or_create(
            title=title,
            parent=None,
            defaults={
                "description": "",
                "owner": owner,
            },
        )
        roots[title] = section

    default_root = roots.get("Авторские") or next(iter(roots.values()))
    owner_ids = list(
        Course.objects.filter(section__isnull=True)
        .values_list("owner_id", flat=True)
        .distinct()
    )
    owner_sections = {}
    for owner_id in owner_ids:
        if owner_id is None:
            continue
        owner_obj = User.objects.filter(pk=owner_id).first()
        if owner_obj is None:
            continue
        get_username = getattr(owner_obj, "get_username", None)
        username = get_username() if callable(get_username) else getattr(owner_obj, "username", str(owner_id))
        title = f"Courses by {username} ({owner_id})"[:255]
        section, _created = Section.objects.get_or_create(
            title=title,
            parent=default_root,
            owner=owner_obj,
            defaults={"description": ""},
        )
        owner_sections[owner_id] = section
        Course.objects.filter(section__isnull=True, owner_id=owner_id).update(section=section)

    Course.objects.filter(section__isnull=True).update(section=default_root)


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0014_contest_moderation_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Section",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional parent section to build nested structure.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="children",
                        to="runner.section",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_sections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        migrations.AddField(
            model_name="course",
            name="section",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="runner.section",
            ),
        ),
        migrations.RunPython(create_root_sections, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="course",
            name="parent",
        ),
        migrations.AlterField(
            model_name="course",
            name="section",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="runner.section",
            ),
        ),
        migrations.AddIndex(
            model_name="course",
            index=models.Index(fields=["section"], name="runner_course_section_idx"),
        ),
        migrations.AddIndex(
            model_name="section",
            index=models.Index(fields=["parent"], name="runner_section_parent_idx"),
        ),
        migrations.AlterField(
            model_name="contest",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contests",
                to="runner.course",
            ),
        ),
    ]
