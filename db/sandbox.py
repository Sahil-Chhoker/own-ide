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


def _get_exec_command(language: str, code: str, input_data: str | None):
    """
    Generate the shell command and environment variables to execute code in a given language.
    Args:
        language (str): Programming language (e.g., 'python', 'javascript', 'java', 'cpp').
        code (str): The source code to execute.
        input_data (str | None): Optional input data for the program. Default name for input file is 'user_file.txt'.
    Returns:
        Tuple[list[str], dict[str, str]]: Command list and environment variables.
    """
    shell = []

    if input_data is not None:
        shell.append('printf "%s" "$INPUT_DATA" > user_file.txt')

    if language == "python":
        shell.append('printf "%s" "$CODE" > main.py')
        shell.append("python3 main.py")

    elif language == "javascript":
        shell.append('printf "%s" "$CODE" > main.js')
        shell.append("node main.js")

    elif language == "java":
        shell.append('printf "%s" "$CODE" > Main.java')
        shell.append("javac Main.java")
        shell.append("java Main")

    elif language == "cpp":
        shell.append('printf "%s" "$CODE" > main.cpp')
        shell.append("g++ main.cpp -o main")
        shell.append("./main")

    else:
        raise ValueError("Unsupported language")

    cmd = ["sh", "-c", " && ".join(shell)]
    env = {
        "CODE": code,
        "INPUT_DATA": input_data or "",
    }

    return cmd, env


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


FILE:
Python Example with input_data:
{
  "language": "python",
  "code": "with open('user_file.txt', 'r', encoding='utf-8') as f:\n    print(f.read())",
  "input_data": "This text is stored inside user_file.txt and will be printed entirely."
}


Java Example with input_data:
{
  "language": "java",
  "code": "import java.nio.file.*; public class Main { public static void main(String[] args) throws Exception { String content = Files.readString(Path.of(\"user_file.txt\")); System.out.println(\"FILE CONTENT:\"); System.out.println(content); } }",
  "input_data": "Hello from input_data!\nThis text should be written to user_file.txt\nand printed by Java."
}


Javascript Example with input_data:
{
  "language": "javascript",
  "code": "const fs = require('fs');\n\nconsole.log('FILE CONTENT:');\nconst content = fs.readFileSync('user_file.txt', 'utf8');\nconsole.log(content);",
  "input_data": "Hello from input_data!\nThis text should be written to user_file.txt\nand printed by JavaScript."
}


CPP Example with input_data:
{
  "language": "cpp",
  "code": "#include <iostream>\n#include <fstream>\n#include <string>\n\nint main() {\n    std::ifstream file(\"user_file.txt\");\n    if (!file.is_open()) {\n        std::cerr << \"Failed to open user_file.txt\" << std::endl;\n        return 1;\n    }\n\n    std::cout << \"FILE CONTENT:\" << std::endl;\n    std::string line;\n    while (std::getline(file, line)) {\n        std::cout << line << std::endl;\n    }\n\n    file.close();\n    return 0;\n}",
  "input_data": "Hello from input_data!\nThis text should be written to user_file.txt\nand printed by C++."
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
            auto_remove=True,

            # security provisions
            mem_limit="128m",           # Hard memory limit
            memswap_limit="128m",       # Disable swap (stops disk thrashing)
            cpu_period=100000,
            cpu_quota=50000,            # Effectively 0.5 CPU
            pids_limit=20,              # Max 20 processes/threads
            network_disabled=True,      # Total network isolation
        )

        cmd, env = _get_exec_command(request.language, request.code, request.input_data)
        start_time = time.perf_counter()

        try:
            exec_log = await asyncio.wait_for(
                asyncio.to_thread(container.exec_run, cmd=cmd, environment=env, demux=True),
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
                execution_time=TIMEOUT_SECONDS,
                error_type="runtime"
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
