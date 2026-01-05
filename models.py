from pydantic import BaseModel
from typing import Literal

Lang = Literal['python', 'javascript', 'java', 'cpp']

class CodeRequest(BaseModel):
    language: Lang
    code: str
    input_data: str | None = None

class CodeResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
