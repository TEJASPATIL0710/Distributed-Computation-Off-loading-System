import uuid

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from celery_app import celery_app
from tasks import run_general_task, run_numeric_task, run_ml_task, run_render_task

# In a real deployment these would live in a database or environment
# variables, not hardcoded — fine for a project demo.
VALID_API_KEYS = {
    "key-client-alpha": "client-alpha",
    "key-client-beta": "client-beta",
}

app = FastAPI(title="Compute Offload Server — Module 6")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) 

def verify_api_key(x_api_key: str = Header(...)):
    """
    Reads the 'X-API-Key' header from the incoming request.
    Header(...) means it's required — FastAPI automatically returns
    a 422 error if it's missing entirely, before this function even runs.
    """
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return VALID_API_KEYS[x_api_key]  # returns the client name for that key


class TaskRequest(BaseModel):
    task_type: str
    payload: str
    client_id: str = "anonymous"


class SubmitResponse(BaseModel):
    task_id: str
    status: str  # "queued"


@app.get("/")
def health_check():
    return {"status": "server is up", "module": 6}


@app.post("/submit-task", response_model=SubmitResponse)
@limiter.limit("5/minute")
def submit_task(request: Request, task: TaskRequest, client_name: str = Depends(verify_api_key)):
    """
    Notice this returns IMMEDIATELY — it just hands the task
    to Celery and gets back a task_id. The actual execution happens
    later, in a separate worker process, whenever one is free.
    """
    task_dispatch = {
        "general": run_general_task,
        "numeric": run_numeric_task,
        "ml": run_ml_task,
        "render": run_render_task,
    }

    task_fn = task_dispatch.get(task.task_type)
    if task_fn is None:
        return SubmitResponse(task_id="none", status=f"error: task type '{task.task_type}' not supported yet")

    async_result = task_fn.delay(task.payload)
    return SubmitResponse(task_id=async_result.id, status="queued")


@app.get("/task-result/{task_id}")
def get_task_result(task_id: str, client_name: str = Depends(verify_api_key)):
    """
    The client calls this to check on a task it submitted earlier.
    'PENDING' means still queued or running; anything else means done.
    """
    async_result = celery_app.AsyncResult(task_id)
    if async_result.state == "PENDING":
        return {"task_id": task_id, "state": "PENDING", "result": None}
    return {"task_id": task_id, "state": async_result.state, "result": async_result.result}