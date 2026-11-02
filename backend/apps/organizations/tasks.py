from celery import shared_task


@shared_task
def enforce_retention():
    from apps.organizations.retention import enforce_retention as run

    return run()
