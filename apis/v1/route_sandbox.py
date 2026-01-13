import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from uuid import uuid4
from db.db_session import get_db
from db.user import get_optional_current_user
from schemas.code import CodeRequest, CodeStatus
from pymongo.asynchronous.database import AsyncDatabase

from db.sandbox import (
    check_quota,
    create_initial_submission,
    execute_code,
    get_visitor_id,
    update_submission_result,
)

router = APIRouter()


async def run_background_task(
    task_id: str, code_request: CodeRequest, db: AsyncDatabase
):
    await db.submissions.update_one(
        {"task_id": task_id}, {"$set": {"status": "running"}}
    )

    result = await execute_code(code_request)

    final_status = "timeout" if result.error_type == "timeout" else ("completed" if result.exit_code == 0 else "failed")
    await update_submission_result(db, task_id, final_status, result)


@router.post("/", response_model=CodeStatus)
async def submit_code(
    code_request: CodeRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_optional_current_user),
    visitor_id: str = Depends(get_visitor_id),
    quota=Depends(check_quota),
    db: AsyncDatabase = Depends(get_db),
) -> CodeStatus:
    task_id = str(uuid4())

    await create_initial_submission(db, task_id, visitor_id, code_request)

    background_tasks.add_task(run_background_task, task_id, code_request, db)

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
