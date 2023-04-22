# Generated by Django 3.2.18 on 2023-04-19 16:18

from django.utils import timezone
from django.db import migrations, models


def add_created_date_to_existing_jobs(apps, schema_editor):
    Job = apps.get_model("engine", "Job")

    jobs = Job.objects.prefetch_related('segment__task').all()
    for job in jobs:
        task = job.segment.task
        job.created_date = task.created_date

    Job.objects.bulk_update(jobs, fields=['created_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0070_alter_segment_frames'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now, null=True),
            preserve_default=False,
        ),
        migrations.RunPython(add_created_date_to_existing_jobs),
        migrations.AlterField(
            model_name='job',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
