# Generated manually for notebook contest feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('runner', '0023_section_teachers'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add contest_type field to Contest
        migrations.AddField(
            model_name='contest',
            name='contest_type',
            field=models.CharField(
                choices=[('regular', 'Regular (problem-based)'), ('notebook', 'Notebook (cell-based)')],
                default='regular',
                help_text='Type of contest: regular problem-based or notebook-based',
                max_length=20
            ),
        ),
        # Add template_notebook field to Contest
        migrations.AddField(
            model_name='contest',
            name='template_notebook',
            field=models.ForeignKey(
                blank=True,
                help_text='Template notebook for notebook-based contests',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='contest_templates',
                to='runner.notebook'
            ),
        ),
        # Add is_task_cell field to Cell
        migrations.AddField(
            model_name='cell',
            name='is_task_cell',
            field=models.BooleanField(default=False),
        ),
        # Add problem field to Cell
        migrations.AddField(
            model_name='cell',
            name='problem',
            field=models.ForeignKey(
                blank=True,
                help_text='Problem associated with this task cell (for notebook contests)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='task_cells',
                to='runner.problem'
            ),
        ),
        # Create NotebookSubmission model
        migrations.CreateModel(
            name='NotebookSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', '⏳ В очереди'),
                        ('running', '🏃 Выполняется'),
                        ('accepted', '✅ Протестировано'),
                        ('failed', '❌ Ошибка'),
                        ('validation_error', '⚠️ Ошибка валидации'),
                        ('validated', '✅ Валидировано')
                    ],
                    default='pending',
                    max_length=20
                )),
                ('metrics', models.JSONField(blank=True, null=True)),
                ('total_score', models.FloatField(blank=True, null=True)),
                ('contest', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notebook_submissions',
                    to='runner.contest'
                )),
                ('notebook', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='contest_submissions',
                    to='runner.notebook'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notebook_submissions',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
        # Add indexes for NotebookSubmission
        migrations.AddIndex(
            model_name='notebooksubmission',
            index=models.Index(fields=['user', 'contest'], name='notebook_sub_user_contest_idx'),
        ),
    ]
