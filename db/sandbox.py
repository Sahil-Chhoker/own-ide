import time
import docker
from fastapi import Depends, HTTPException, Request, status
from db.redis import get_redis_client
from db.user import get_optional_current_user
from schemas.code import CodeRequest, CodeResult
from core.config import settings

client = docker.from_env()


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


def execute_code(request: CodeRequest) -> CodeResult:
    image = settings.LANG_IMAGE.get(request.language)
    if not image:
        return CodeResult(stdout=None, stderr="Unsupported language", exit_code=1)

    container = None
    try:
        container = client.containers.run(
            image=image, command=["sleep", "infinity"], detach=True, auto_remove=True
        )

        exec_command = _get_exec_command(request.language, request.code)

        start_time = time.perf_counter()
        exec_log = container.exec_run(exec_command, demux=True)
        end_time = time.perf_counter()

        # Calculate duration and remove 50ms buffer
        total_time = end_time - start_time
        execution_time = max(0.0, total_time - 0.05)

        exit_code = exec_log.exit_code
        stdout_bytes, stderr_bytes = exec_log.output

        stdout = (
            stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else None
        )
        stderr = (
            stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else None
        )

        error_type = None
        if exit_code != 0:
            error_type = "compile" if not stdout and stderr else "runtime"

        return CodeResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time=round(execution_time, 4),
            error_type=error_type,
        )

    except Exception as e:
        return CodeResult(stdout=None, stderr=str(e), exit_code=1, error_type="system")

    finally:
        if container:
            container.stop()


async def check_quota(
    request: Request,
    user=Depends(get_optional_current_user),
    redis=Depends(get_redis_client),
):
    """
    Check and enforce guest user quota based on IP address.
    """
    # Authorized users have no quota restrictions
    if user:
        return

    client_ip = request.client.host
    redis_key = f"quota:{client_ip}"

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
