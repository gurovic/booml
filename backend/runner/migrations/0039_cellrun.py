import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('runner', '0038_teacheraccessrequest'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CellRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('running', 'Выполняется'),
                        ('finished', 'Завершено'),
                        ('error', 'Ошибка'),
                    ],
                    default='running',
                    max_length=16,
                )),
                ('run_id', models.CharField(blank=True, db_index=True, max_length=64)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('cell', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='runs',
                    to='runner.cell',
                )),
                ('notebook', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cell_runs',
                    to='runner.notebook',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='cell_runs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Запуск ячейки',
                'verbose_name_plural': 'Очередь выполнения ячеек',
                'ordering': ['-started_at'],
            },
        ),
    ]
