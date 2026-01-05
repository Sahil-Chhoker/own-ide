from models import CodeRequest, CodeResult
import docker

client = docker.from_env()

# language to Docker image mapping
LANG_IMAGE = {
    "python": "python:3.12-alpine",
    "javascript": "node:20-alpine",
    "java": "eclipse-temurin:21-jre-alpine",
    "cpp": "gcc:13-alpine",
    "ruby": "ruby:3.3-alpine",
}


def execute_code(request: CodeRequest) -> CodeResult:
    print(  "Executing code in language:", request.language)
    image = LANG_IMAGE.get(request.language)
    if not image:
        return CodeResult(stdout="", stderr="Unsupported language", exit_code=1)
    
    try:
        container = client.containers.run(
            image=image,
            command=["sleep", "infinity"],
            detach=True,
            auto_remove=True
        )
        exec_command = ["python3", "-c", request.code]
        exec_log = container.exec_run(exec_command, demux=True)
        stdout, stderr = exec_log.output
        stdout = stdout.decode() if stdout else ""
        stderr = stderr.decode() if stderr else ""
        exit_code = exec_log.exit_code
        container.stop()
        return CodeResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
    except Exception as e:
        return CodeResult(stdout="", stderr=str(e), exit_code=1)