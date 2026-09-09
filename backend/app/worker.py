from __future__ import annotations

from app.queue import celery_app

if celery_app is not None:
    from app.api.v1.endpoints.jobs import process_job_task

    @celery_app.task(name="app.worker.process_job", bind=True, max_retries=2, acks_late=True)
    def process_job(self, job_id: str, input_paths: list[str], tool_slug: str, options: dict, user_id: str = "local-dev") -> None:
        try:
            process_job_task(job_id, input_paths, tool_slug, options, user_id)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30)
else:
    process_job = None
