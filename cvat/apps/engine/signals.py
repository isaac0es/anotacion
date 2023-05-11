# Copyright (C) 2019-2022 Intel Corporation
# Copyright (C) 2023 CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT
import shutil

from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (Annotation, CloudStorage, Data, Job, Profile, Project,
    StatusChoice, Task, QualitySettings)

from cvat.apps.engine import quality_control as qc


# TODO: need to log any problems reported by shutil.rmtree when the new
# analytics feature is available. Now the log system can write information
# into a file inside removed directory.

@receiver(post_save, sender=Job,
    dispatch_uid=__name__ + ".save_job_handler")
def __save_job_handler(instance, created, **kwargs):
    # no need to update task status for newly created jobs
    if created:
        return

    db_task = instance.segment.task
    db_jobs = list(Job.objects.filter(segment__task_id=db_task.id))
    status = StatusChoice.COMPLETED
    if any(db_job.status == StatusChoice.ANNOTATION for db_job in db_jobs):
        status = StatusChoice.ANNOTATION
    elif any(db_job.status == StatusChoice.VALIDATION for db_job in db_jobs):
        status = StatusChoice.VALIDATION

    if status != db_task.status:
        db_task.status = status
        db_task.save()

@receiver(post_save, sender=User,
    dispatch_uid=__name__ + ".save_user_handler")
def __save_user_handler(instance, **kwargs):
    if not hasattr(instance, 'profile'):
        profile = Profile()
        profile.user = instance
        profile.save()

@receiver(post_delete, sender=Project,
    dispatch_uid=__name__ + ".delete_project_handler")
def __delete_project_handler(instance, **kwargs):
    shutil.rmtree(instance.get_dirname(), ignore_errors=True)

@receiver(post_delete, sender=Task,
    dispatch_uid=__name__ + ".delete_task_handler")
def __delete_task_handler(instance, **kwargs):
    shutil.rmtree(instance.get_dirname(), ignore_errors=True)
    if instance.data and not instance.data.tasks.exists():
        instance.data.delete()

    try:
        if instance.project: # update project
            db_project = instance.project
            db_project.save()
    except Project.DoesNotExist:
        pass # probably the project has been deleted

@receiver(post_delete, sender=Job,
    dispatch_uid=__name__ + ".delete_job_handler")
def __delete_job_handler(instance, **kwargs):
    shutil.rmtree(instance.get_dirname(), ignore_errors=True)

@receiver(post_delete, sender=Data,
    dispatch_uid=__name__ + ".delete_data_handler")
def __delete_data_handler(instance, **kwargs):
    shutil.rmtree(instance.get_data_dirname(), ignore_errors=True)

@receiver(post_delete, sender=CloudStorage,
    dispatch_uid=__name__ + ".delete_cloudstorage_handler")
def __delete_cloudstorage_handler(instance, **kwargs):
    shutil.rmtree(instance.get_storage_dirname(), ignore_errors=True)


@receiver(post_save, sender=Job,
    dispatch_uid=__name__ + ".save_job-update_quality_metrics")
@receiver(post_save, sender=Task,
    dispatch_uid=__name__ + ".save_task-update_quality_metrics")
@receiver(post_save, sender=Project,
    dispatch_uid=__name__ + ".save_project-update_quality_metrics")
@receiver(post_save, sender=Annotation,
    dispatch_uid=__name__ + ".save_annotation-update_quality_metrics")
def __save_job__update_quality_metrics(instance, created, **kwargs):
    tasks = []

    if isinstance(instance, Project):
        tasks += list(instance.tasks.all())
    elif isinstance(instance, Task):
        tasks.append(instance)
    elif isinstance(instance, Job):
        tasks.append(instance.segment.task)
    elif isinstance(instance, Annotation):
        tasks.append(instance.job.segment.task)
    else:
        assert False

    for task in tasks:
        qc.QueueJobManager().schedule_quality_check_job(task)


@receiver(post_save, sender=Task,
    dispatch_uid=__name__ + ".save_task-initialize_quality_settings")
def __save_task__initialize_quality_settings(instance, created, **kwargs):
    # Initializes default quality settings for the task
    # this is done here to make the components decoupled
    if created:
        QualitySettings.objects.get_or_create(task=instance)
