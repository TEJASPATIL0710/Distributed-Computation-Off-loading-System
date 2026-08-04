import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from celery_app import celery_app
from tasks import run_general_task, run_numeric_task, run_ml_task, run_render_task

app = FastAPI(title="Compute Offload Server — Module 3")


class TaskRequest(BaseModel):
    task_type: str
    payload: str
    client_id: str = "anonymous"


class SubmitResponse(BaseModel):
    task_id: str
    status: str  # "queued"


@app.get("/")
def health_check():
    return {"status": "server is up", "module": 3}


@app.post("/submit-task", response_model=SubmitResponse)
def submit_task(task: TaskRequest):
    """
    Notice this returns IMMEDIATELY now — it just hands the task
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
def get_task_result(task_id: str):
    """
    The client calls this to check on a task it submitted earlier.
    'PENDING' means still queued or running; anything else means done.
    """
    async_result = celery_app.AsyncResult(task_id)
    if async_result.state == "PENDING":
        return {"task_id": task_id, "state": "PENDING", "result": None}
    return {"task_id": task_id, "state": async_result.state, "result": async_result.result}