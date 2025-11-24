from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("runner", "0003_problem_descriptor_metrics"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="test_data",
            field=models.JSONField(
                blank=True,
                help_text="Дополнительная информация, полученная от тестирующей системы",
                null=True,
                verbose_name="Данные тестирования",
            ),
        ),
        migrations.AlterField(
            model_name="cell",
            name="cell_type",
            field=models.CharField(
                choices=[("code", "Code"), ("latex", "LaTeX"), ("text", "Text")],
                default="code",
                max_length=16,
            ),
        ),
    ]