import threading
import time

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

def heartbeat_loop(hostname):
    """
    Runs forever in a background thread, refreshing this worker's
    Redis entry every 15 seconds — regardless of whether the worker
    is busy or idle. This keeps the worker visible on the dashboard
    even during long idle stretches, without needing to wait for a
    task to complete.
    """
    from tasks import dashboard_redis, mark_idle
    import json

    while True:
        key = f"worker_status:{hostname}"
        existing = dashboard_redis.get(key)
        if existing:
            # Worker already has a status (busy or idle) — just extend
            # its expiry without changing what it says.
            dashboard_redis.expire(key, 60)
        else:
            # No entry at all (e.g. it expired) — recreate as idle.
            mark_idle(hostname)
        time.sleep(15)


@worker_ready.connect
def announce_worker(sender=None, **kwargs):
    from tasks import mark_idle
    mark_idle(sender.hostname)

    # Start the background heartbeat thread once, when the worker starts up.
    t = threading.Thread(target=heartbeat_loop, args=(sender.hostname,), daemon=True)
    t.start()