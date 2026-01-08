from fastapi import FastAPI, BackgroundTasks, HTTPException
from uuid import uuid4
from schemas.code import CodeRequest, CodeStatus

from execute import execute_code

app = FastAPI()
tasks_db = {}


def run_background_task(task_id: str, code_request: CodeRequest):
    tasks_db[task_id]["status"] = "running"
    result = execute_code(code_request)
    if result.exit_code == 0:
        tasks_db[task_id]["status"] = "completed"
    else:
        tasks_db[task_id]["status"] = "failed"
    tasks_db[task_id]["result"] = result


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/sandbox/", response_model=CodeStatus)
async def submit_code(
    request: CodeRequest, background_tasks: BackgroundTasks
) -> CodeStatus:
    task_id = str(uuid4())
    tasks_db[task_id] = {"status": "pending", "result": None}
    background_tasks.add_task(run_background_task, task_id, request)
    return CodeStatus(
        task_id=task_id, user_id="request.id", status="pending", result=None
    )


@app.get("/status/{task_id}", response_model=CodeStatus)
async def get_status(task_id: str) -> CodeStatus:
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    return CodeStatus(
        task_id=task_id,
        user_id="request.id",
        status=tasks_db[task_id]["status"],
        result=tasks_db[task_id]["result"],
    )
