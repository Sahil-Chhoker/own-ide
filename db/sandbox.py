import asyncio
from datetime import datetime, timedelta, timezone
import os
import time
from uuid import uuid4
import docker
from fastapi import Depends, HTTPException, Request, Response, status
from db.redis_session import get_redis_client
from db.user import get_optional_current_user
from schemas.code import CodeRequest, CodeResult
from core.config import settings
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.write_concern import WriteConcern


_docker_client = None
TIMEOUT_SECONDS = 5

def get_docker_client():
    global _docker_client
    if _docker_client:
        return _docker_client

    base_url = os.getenv("DOCKER_HOST", "tcp://dind:2375")

    max_retries = 15 
    for i in range(max_retries):
        try:
            print(f"Attempting to connect to Docker (Attempt {i+1}/{max_retries})...")
            client = docker.DockerClient(base_url=base_url, timeout=10)
            client.ping()
            print("Successfully connected to Docker daemon.")
            _docker_client = client
            return _docker_client
        except (docker.errors.DockerException, Exception) as e:
            if i == max_retries - 1:
                print("Could not connect to Docker daemon after 15 attempts.")
                raise e
            # Wait longer as attempts increase (2s, 4s, 6s...)
            time.sleep(min(i * 2, 10) + 2) 

    return None


def _get_exec_command(language: str, code: str) -> list[str]:
    if language == "java":
        return [
            "sh",
            "-c",
            f'echo "{code}" > Main.java && javac Main.java && java Main',
        ]
    elif language == "cpp":
        return [
            "sh",
            "-c",
            f'echo "{code}" > main.cpp && g++ main.cpp -o main && ./main',
        ]
    elif language in settings.EXEC_CMD:
        return settings.EXEC_CMD[language] + [code]
    else:
        raise ValueError("Unsupported language")


"""
Sample Json for python:
{
    "language": "python",
    "code": "print(\"Hello, World!\")\nprint(\"I am learning Python.\")",
    "input_data": null
}


Sample Json for java:
{
    "language": "java",
    "code": "public class Main { public static void main(String[] args) { System.out.println(\\\"Hello, World!\\\"); System.out.println(\\\"I am learning Java.\\\"); } }",
    "input_data": null
}


Sample Json for JavaScript:
{
    "language": "javascript",
    "code": "console.log('Hello, World!'); console.log('I am learning JavaScript.');",
    "input_data": null
}


Sample Json for C++:
{
    "language": "cpp",
    "code": "#include <iostream>\n\nint main() {\n    std::cout << \\\"Hello, World!\\\" << std::endl;\n    return 0;\n}",
    "input_data": null
}
"""


async def execute_code(request: CodeRequest) -> CodeResult:
    image = settings.LANG_IMAGE.get(request.language)
    if not image:
        return CodeResult(stdout=None, stderr="Unsupported language", exit_code=1)

    client = await asyncio.to_thread(get_docker_client)
    container = None
    
    try:
        container = await asyncio.to_thread(
            client.containers.run,
            image=image, 
            command=["sleep", "infinity"], 
            detach=True, 
            auto_remove=True
        )

        exec_command = _get_exec_command(request.language, request.code)
        start_time = time.perf_counter()

        try:
            exec_log = await asyncio.wait_for(
                asyncio.to_thread(container.exec_run, exec_command, demux=True),
                timeout=TIMEOUT_SECONDS
            )
            
            end_time = time.perf_counter()
            execution_time = max(0.0, (end_time - start_time) - 0.05)

            stdout_bytes, stderr_bytes = exec_log.output
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else None
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else None

            return CodeResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exec_log.exit_code,
                execution_time=round(execution_time, 4),
                error_type="compile" if not stdout and stderr and exec_log.exit_code != 0 else ("runtime" if exec_log.exit_code != 0 else None),
            )

        except asyncio.TimeoutError:
            return CodeResult(
                stdout=None, 
                stderr="Execution timed out after 5 seconds", 
                exit_code=124, # Standard Linux timeout exit code
                execution_time=5.0,
                error_type="timeout"
            )

    except Exception as e:
        return CodeResult(stdout=None, stderr=str(e), exit_code=1, error_type="system")

    finally:
        if container:
            await asyncio.to_thread(container.stop, timeout=1)


async def create_initial_submission(
    db: AsyncDatabase, task_id: str, user_id: str, code_request: CodeRequest
):
    now = datetime.now(timezone.utc)
    is_guest = user_id.startswith("guest_") or user_id == "guest"

    if is_guest:
        expiration_time = now + timedelta(seconds=600)
    else:
        expiration_time = now + timedelta(seconds=settings.SUBMISSION_TTL_SECONDS)

    submission_data = {
        "task_id": task_id,
        "user_id": user_id,
        "language": code_request.language,
        "code": code_request.code,
        "status": "pending",
        "result": None,
        "created_at": now,
        "expireAt": expiration_time,
    }
    await db.submissions.with_options(
        write_concern=WriteConcern(w=1)
    ).insert_one(submission_data)


async def update_submission_result(
    db: AsyncDatabase, task_id: str, status: str, result: CodeResult
):
    await db.submissions.update_one(
        {"task_id": task_id},
        {
            "$set": {
                "status": status,
                "result": result.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


async def get_visitor_id(
    request: Request, response: Response, user=Depends(get_optional_current_user)
) -> str:
    # if logged in, use user ID
    if user:
        return user.id

    # if not logged in, check for an existing guest_id cookie
    guest_id = request.cookies.get("guest_id")

    # if no cookie, create a new one for this visitor
    if not guest_id:
        guest_id = f"guest_{uuid4()}"
        # Set cookie to expire in 30 days
        response.set_cookie(
            key="guest_id", value=guest_id, max_age=2592000, httponly=True
        )

    return guest_id


async def check_quota(
    visitor_id: str = Depends(get_visitor_id),
    user=Depends(get_optional_current_user),
    redis=Depends(get_redis_client),
):
    """
    Check and enforce guest user quota based on IP address.
    """
    # Authorized users have no quota restrictions
    if user:
        return

    redis_key = f"quota:{visitor_id}"

    count = await redis.get(redis_key)
    if count and int(count) >= settings.GUEST_QUOTA:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Guest quota exceeded. Please log in for unlimited access.",
        )
    async with redis.pipeline(transaction=True) as pipe:
        await pipe.incr(redis_key)
        await pipe.expire(redis_key, settings.IP_EXPIRY_SECONDS, nx=True)
        await pipe.execute()
