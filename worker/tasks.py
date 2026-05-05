import asyncio
import logging

from schemas.code import CodeRequest

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="sandbox.run_code_execution")
def run_code_execution_task(task_id: str, code_request_dict: dict) -> dict:
    """Run sandbox execution in a Celery worker process."""
    code_request = CodeRequest.model_validate(code_request_dict)

    from db.sandbox import process_execution_job

    return asyncio.run(process_execution_job(task_id, code_request))
