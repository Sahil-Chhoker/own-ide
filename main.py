from fastapi import FastAPI
from models import CodeRequest, CodeResult

from execute import execute_code

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/sandbox/")
async def read_sandbox(code_request: CodeRequest) -> CodeResult:
    return execute_code(code_request)