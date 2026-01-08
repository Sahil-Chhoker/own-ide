from pydantic import BaseModel, EmailStr
from typing import Literal


class CodeRequest(BaseModel):
    language: Literal["python", "javascript", "java", "cpp"]
    code: str
    input_data: str | None = None


class CodeResult(BaseModel):
    stdout: str | None = None
    stderr: str | None = None
    error_type: Literal["runtime", "compile", "system"] | None = None
    exit_code: int | None = None
    execution_time: float | None = None


class CodeStatus(BaseModel):
    task_id: str
    user_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: CodeResult | None = None
