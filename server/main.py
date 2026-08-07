import uuid
import json
import time
import redis as redis_lib

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from celery_app import celery_app
from tasks import run_general_task, run_numeric_task, run_ml_task, run_render_task
from fastapi.responses import FileResponse

# In a real deployment these would live in a database or environment
# variables, not hardcoded — fine for a project demo.
VALID_API_KEYS = {
    "key-client-alpha": "client-alpha",
    "key-client-beta": "client-beta",
}

dashboard_redis = redis_lib.Redis(host="localhost", port=6379, db=1, decode_responses=True)
# Using db=1 here (not db=0, which Celery uses) keeps our dashboard
# data cleanly separated from Celery's internal broker/result data.

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
@limiter.limit("20/minute")
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
    log_entry = {
        "task_id": async_result.id,
        "task_type": task.task_type,
        "client": client_name,
        "submitted_at": time.time(),
    }
    dashboard_redis.lpush("task_log", json.dumps(log_entry))
    dashboard_redis.ltrim("task_log", 0, 49) #keep only the most recent 50 log_entries
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

@app.get("/dashboard-data")
def dashboard_data():
    # Queue depth: how many tasks are waiting in Celery's default queue
    queue_length = celery_app.connection().default_channel.client.llen("celery")

    # Active workers and what they're currently running — read from our
    # own Redis-based tracking, since Celery's built-in inspect() can time
    # out on busy workers under the --pool=solo mode (Windows workaround).
    worker_status = []
    for key in dashboard_redis.scan_iter("worker_status:*"):
        hostname = key.split("worker_status:")[1]
        status = json.loads(dashboard_redis.get(key))
        worker_status.append({
            "worker": hostname,
            "busy": status["busy"],
            "current_tasks": [status["task"]] if status["task"] else [],
        })

    # Recent task history, with live state looked up per task
    raw_log = dashboard_redis.lrange("task_log", 0, 19)  # most recent 20
    history = []
    for entry_json in raw_log:
        entry = json.loads(entry_json)
        result = celery_app.AsyncResult(entry["task_id"])
        worker_name = "-"
        if result.state == "SUCCESS" and isinstance(result.result, dict):
            worker_name = result.result.get("worker", "-")
        history.append({
            "task_id": entry["task_id"][:8],
            "task_type": entry["task_type"],
            "client": entry["client"],
            "state": result.state,
            "worker": worker_name,
            "submitted_at": entry["submitted_at"],
        })

    return {
        "queue_length": queue_length,
        "workers": worker_status,
        "busy_workers": sum(1 for w in worker_status if w["busy"]),
        "recent_tasks": history,
    }

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/dashboard.html")