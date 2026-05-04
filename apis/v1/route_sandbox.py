from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4
from db.db_session import get_db
from db.user import get_optional_current_user
from schemas.code import CodeRequest, CodeStatus
from pymongo.asynchronous.database import AsyncDatabase

from db.sandbox import (
    check_quota,
    create_initial_submission,
    get_visitor_id,
)
from worker.tasks import run_code_execution_task

router = APIRouter()


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
        run_code_execution_task.delay(task_id, code_request.model_dump(mode="json"))
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

    return CodeStatus(
        task_id=submission["task_id"],
        user_id=submission["user_id"],
        status=submission["status"],
        result=submission["result"],
    )
