from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4
from celery.result import AsyncResult
from db.db_session import get_db
from db.user import get_optional_current_user
from schemas.code import CodeRequest, CodeResult, CodeStatus
from pymongo.asynchronous.database import AsyncDatabase

from db.sandbox import (
    check_quota,
    create_initial_submission,
    get_visitor_id,
)
from worker.celery_app import celery_app
from worker.tasks import run_code_execution_task

router = APIRouter()


def _map_celery_state(state: str) -> str:
    """Normalize Celery states to API-facing status values."""
    if state in {"PENDING", "RECEIVED"}:
        return "pending"
    if state == "STARTED":
        return "running"
    if state == "RETRY":
        return "retrying"
    if state == "SUCCESS":
        return "completed"
    return "failed"


@router.post("/", response_model=CodeStatus)
async def submit_code(
    code_request: CodeRequest,
    user=Depends(get_optional_current_user),
    visitor_id: str = Depends(get_visitor_id),
    quota=Depends(check_quota),
    db: AsyncDatabase = Depends(get_db),
) -> CodeStatus:
    task_id = str(uuid4())

    await create_initial_submission(db, task_id, visitor_id, code_request)

    try:
        # Keep API task_id and Celery task id identical for simple status polling.
        run_code_execution_task.apply_async(
            args=[task_id, code_request.model_dump(mode="json")],
            task_id=task_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Execution queue is unavailable. Try again later.",
        ) from exc

    return CodeStatus(
        task_id=task_id, user_id=visitor_id, status="pending", result=None
    )


@router.get("/status/{task_id}", response_model=CodeStatus)
async def get_status(task_id: str, db: AsyncDatabase = Depends(get_db)) -> CodeStatus:
    submission = await db.submissions.find_one({"task_id": task_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Task not found")

    async_result = AsyncResult(task_id, app=celery_app)
    normalized_status = _map_celery_state(async_result.state)

    # Prefer MongoDB as source of truth
    if submission.get("result") is not None:
        return CodeStatus(
            task_id=task_id,
            user_id=submission["user_id"],
            status=submission.get("status", normalized_status),
            result=submission.get("result"),
        )

    if async_result.successful():
        res_data = async_result.result or {}
        # Celery backend might have the result before Mongo is updated; return it and backfill Mongo.
        celery_status = res_data.get("status") or submission.get("status") or "completed"
        celery_result = res_data.get("result")
        if celery_result is not None:
            await db.submissions.update_one(
                {"task_id": task_id},
                {"$set": {"status": celery_status, "result": celery_result}},
            )
        return CodeStatus(
            task_id=task_id,
            user_id=submission["user_id"],
            status=celery_status,
            result=celery_result,
        )

    if async_result.failed():
        # Fallback if MongoDB didn't capture the worker crash: create and persist a system error.
        result = None
        if async_result.traceback:
            result = CodeResult(
                stdout=None,
                stderr=f"Internal Worker Error:\n{async_result.traceback}",
                error_type="system",
                exit_code=1,
                execution_time=None,
            ).model_dump()
            await db.submissions.update_one(
                {"task_id": task_id},
                {"$set": {"status": "failed", "result": result}},
            )

        return CodeStatus(
            task_id=task_id,
            user_id=submission["user_id"],
            status=submission.get("status", "failed"),
            result=result,
        )

    return CodeStatus(
        task_id=task_id,
        user_id=submission["user_id"],
        status=submission.get("status", normalized_status),
        result=None,
    )
