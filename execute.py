from models import CodeRequest, CodeResult
import docker

client = docker.from_env()

# language to Docker image mapping
LANG_IMAGE = {
    "python": "python:3.12-alpine",
    "javascript": "node:20-alpine",
    "java": "eclipse-temurin:21-jdk-alpine",
    "cpp": "gcc:13.4.0-bookworm",
}

EXEC_CMD = {
    "python": ["python3", "-c"],
    "javascript": ["node", "-e"],
    "java": [],  # Java needs compilation; handled differently
    "cpp": [],   # C++ needs compilation; handled differently
}


def _get_exec_command(language: str, code: str) -> list[str]:
    if language in EXEC_CMD:
        if language == "java":
            # For Java, we need to write code to a file, compile and run
            return ["sh", "-c", f'echo "{code}" > Main.java && javac Main.java && java Main']
        elif language == "cpp":
            # For C++, we need to write code to a file, compile and run
            return ["sh", "-c", f'echo "{code}" > main.cpp && g++ main.cpp -o main && ./main']
        else:
            return EXEC_CMD[language] + [code]
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
    "code": "#include <iostream>\n\nint main() {\n    std::cout << \\\"Hello, World!\\\" << std::endl;\n    return 0;\n}"
    "input_data": null
}
"""

def execute_code(request: CodeRequest) -> CodeResult:
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
        exec_command = _get_exec_command(request.language, request.code)

        # execute code and format output
        exec_log = container.exec_run(exec_command, demux=True)
        exit_code = exec_log.exit_code
        stdout, stderr = exec_log.output
        stdout = stdout.decode() if stdout else ""
        stderr = stderr.decode() if stderr else ""

        container.stop()

        return CodeResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

    except Exception as e:
        return CodeResult(stdout="", stderr=str(e), exit_code=1)