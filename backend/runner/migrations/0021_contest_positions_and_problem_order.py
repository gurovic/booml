from django.db import migrations, models


def forwards(apps, schema_editor):
    Contest = apps.get_model("runner", "Contest")
    ContestProblem = apps.get_model("runner", "ContestProblem")

    # Backfill contest positions per course to preserve current ordering (newest first).
    course_ids = (
        Contest.objects.order_by()
        .values_list("course_id", flat=True)
        .distinct()
    )
    for course_id in course_ids:
        contests = list(
            Contest.objects.filter(course_id=course_id).order_by("-created_at", "-id")
        )
        for idx, contest in enumerate(contests):
            contest.position = idx
        if contests:
            Contest.objects.bulk_update(contests, ["position"])

    # Backfill problem positions per contest based on insertion order of the M2M rows.
    contest_ids = (
        ContestProblem.objects.order_by()
        .values_list("contest_id", flat=True)
        .distinct()
    )
    for contest_id in contest_ids:
        links = list(
            ContestProblem.objects.filter(contest_id=contest_id).order_by("id")
        )
        for idx, link in enumerate(links):
            link.position = idx
        if links:
            ContestProblem.objects.bulk_update(links, ["position"])


def backwards(apps, schema_editor):
    # Best-effort: reset positions to 0.
    Contest = apps.get_model("runner", "Contest")
    ContestProblem = apps.get_model("runner", "ContestProblem")
    Contest.objects.all().update(position=0)
    ContestProblem.objects.all().update(position=0)


class Migration(migrations.Migration):
    dependencies = [
        ("runner", "0020_alter_submission_status"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contest",
            options={"ordering": ["position", "-created_at"]},
        ),
        migrations.AddField(
            model_name="contest",
            name="position",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.SeparateDatabaseAndState(
            # The table runner_contest_problems already exists (auto-generated M2M table).
            # We only want to add a model state for it, not create/drop the table.
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ContestProblem",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("position", models.PositiveIntegerField(db_index=True, default=0)),
                        ("contest", models.ForeignKey(on_delete=models.deletion.CASCADE, to="runner.contest")),
                        ("problem", models.ForeignKey(on_delete=models.deletion.CASCADE, to="runner.problem")),
                    ],
                    options={
                        "db_table": "runner_contest_problems",
                        "ordering": ["position", "id"],
                        "unique_together": {("contest", "problem")},
                        "indexes": [
                            models.Index(fields=["contest", "position"], name="runner_contestprob_pos_idx"),
                        ],
                    },
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            # Swapping auto-M2M to explicit through model is a state change only:
            # db_table stays the same and data is preserved.
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="contest",
                    name="problems",
                    field=models.ManyToManyField(
                        blank=True,
                        related_name="contests",
                        through="runner.ContestProblem",
                        to="runner.problem",
                    ),
                ),
            ],
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE runner_contest_problems "
                "ADD COLUMN IF NOT EXISTS position integer NOT NULL DEFAULT 0;"
            ),
            reverse_sql=(
                "ALTER TABLE runner_contest_problems "
                "DROP COLUMN IF EXISTS position;"
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
