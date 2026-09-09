from __future__ import annotations

from typing import Any

from app.core.config import settings


celery_app = None
if settings.REDIS_URL:
    from celery import Celery

    celery_app = Celery("lunu_wps", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
    celery_app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True, task_track_started=True, worker_prefetch_multiplier=1)


def enqueue_job(job_id: str, input_paths: list[str], tool_slug: str, options: dict[str, Any], user_id: str) -> str | None:
    """Dispatch to Redis when configured; return None for local fallback."""
    if celery_app is None:
        return None
    celery_app.send_task("app.worker.process_job", args=[job_id, input_paths, tool_slug, options, user_id])
    return job_id
