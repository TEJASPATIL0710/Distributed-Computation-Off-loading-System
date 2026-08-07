from celery import Celery

celery_app = Celery(
    "compute_offload",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 3600  # results kept for 1 hour, then cleaned up
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.broker_transport_options = {"visibility_timeout": 30}

import tasks  # noqa: E402 — must come after celery_app is defined, registers our tasks
from celery.signals import worker_ready

@worker_ready.connect
def announce_worker(sender=None, **kwargs):
    from tasks import mark_idle
    mark_idle(sender.hostname)