from __future__ import annotations

import logging

from app.queue import celery_app
from app.core.logging import configure_logging

logger = logging.getLogger("officeflow.worker")

if celery_app is not None:
    from app.api.v1.endpoints.jobs import process_job_task

    @celery_app.task(
        name="app.worker.process_job",
        bind=True,
        max_retries=3,
        acks_late=True,
        autoretry_for=(ConnectionError, TimeoutError),
        retry_backoff=True,
        retry_backoff_max=120,
        retry_jitter=True,
    )
    def process_job(self, job_id: str, input_paths: list[str], tool_slug: str, options: dict, user_id: str = "local-dev") -> None:
        configure_logging()
        try:
            logger.info("job_started", extra={"job_id": job_id, "document_id": job_id, "tool_slug": tool_slug, "retry_count": self.request.retries})
            process_job_task(job_id, input_paths, tool_slug, options, user_id)
            logger.info("job_finished", extra={"job_id": job_id, "document_id": job_id, "tool_slug": tool_slug, "retry_count": self.request.retries})
        except (ConnectionError, TimeoutError) as exc:
            logger.warning("transient_job_failure", exc_info=True, extra={"job_id": job_id, "document_id": job_id, "tool_slug": tool_slug, "retry_count": self.request.retries})
            raise self.retry(exc=exc, countdown=min(120, 15 * (2 ** self.request.retries)))
        except Exception:
            logger.exception("job_failed", extra={"job_id": job_id, "document_id": job_id, "tool_slug": tool_slug, "retry_count": self.request.retries})
            raise
else:
    process_job = None
