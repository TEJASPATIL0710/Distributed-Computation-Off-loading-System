import uuid
import json
import time
import redis as redis_lib
import csv
import io

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from celery_app import celery_app
from tasks import run_general_task, run_numeric_task, run_ml_task, run_render_task, run_multilang_task, mark_busy
from fastapi.responses import FileResponse, StreamingResponse
from tasks import ARTIFACT_ROOT
from database import get_connection
from auth import verify_password, create_access_token, decode_access_token
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from fastapi.staticfiles import StaticFiles

dashboard_redis = redis_lib.Redis(host="localhost", port=6379, db=1, decode_responses=True)
# Using db=1 here (not db=0, which Celery uses) keeps our dashboard
# data cleanly separated from Celery's internal broker/result data.

app = FastAPI(title="Compute Offload Server — Module 6")
app.mount("/static", StaticFiles(directory="static"), name="static")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) 

def verify_token(authorization: str = Header(...)) -> str:
    """
    Reads the 'Authorization' header, expected format: 'Bearer <token>'.
    Returns the username if the token is valid.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization.removeprefix("Bearer ")
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return username

def query_task_logs(username: str = None, task_type: str = None, state: str = None):
    """
    Fetches task logs with optional filters. Any filter left as None
    is skipped — e.g. calling this with no arguments returns everything.
    """
    conn = get_connection()
    query = "SELECT * FROM task_logs WHERE 1=1"
    params = []

    if username:
        query += " AND username = ?"
        params.append(username)
    if task_type:
        query += " AND task_type = ?"
        params.append(task_type)
    if state:
        query += " AND state = ?"
        params.append(state)

    query += " ORDER BY submitted_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

class TaskRequest(BaseModel):
    task_type: str
    payload: str
    client_id: str = "anonymous"
    language: str = "python"  # only used when task_type == "multilang"

class SubmitResponse(BaseModel):
    task_id: str
    status: str  # "queued"

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@app.get("/")
def health_check():
    return {"status": "server is up", "module": 6}

@app.post("/submit-task", response_model=SubmitResponse)
@limiter.limit("20/minute")
def submit_task(request: Request, task: TaskRequest, client_name: str = Depends(verify_token)):
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

    if task.task_type == "multilang":
        async_result = run_multilang_task.delay(task.payload, task.language)
    else:
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

    conn = get_connection()
    conn.execute(
        """INSERT INTO task_logs (task_id, username, ip_address, task_type, submitted_at) VALUES (?, ?, ?, ?, ?)""",
        (
            async_result.id,
            client_name,
            request.client.host,
            task.task_type,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return SubmitResponse(task_id=async_result.id, status="queued")

@app.get("/task-result/{task_id}")
def get_task_result(task_id: str, client_name: str = Depends(verify_token)):
    """
    The client calls this to check on a task it submitted earlier.
    'PENDING' means still queued or running; anything else means done.
    """
    async_result = celery_app.AsyncResult(task_id)

    if async_result.state == "PENDING":
        return {"task_id": task_id, "state": "PENDING", "result": None}

    # Task is done (success or error) — update the permanent log with
    # the outcome, but only if we haven't already recorded it (avoids
    # rewriting the same row every time the client polls after completion).
    conn = get_connection()
    existing = conn.execute(
        "SELECT state FROM task_logs WHERE task_id = ?", (task_id,)
    ).fetchone()

    if existing and existing["state"] is None:
        result = async_result.result if isinstance(async_result.result, dict) else {}
        conn.execute(
            """UPDATE task_logs SET state = ?, stderr = ?, execution_time_sec = ? WHERE task_id = ?""",
            (
                async_result.state,
                result.get("stderr", ""),
                result.get("execution_time_sec"),
                task_id,
            ),
        )
        conn.commit()
    conn.close()

    return {"task_id": task_id, "state": async_result.state, "result": async_result.result}


@app.get("/task-artifact/{task_id}/{artifact_name:path}")
def get_task_artifact(task_id: str, artifact_name: str, client_name: str = Depends(verify_token)):
    """Download a file produced by a successful render task."""
    task_root = (ARTIFACT_ROOT / task_id).resolve()
    artifact_path = (task_root / artifact_name).resolve()
    if task_root not in artifact_path.parents or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(
        artifact_path,
        media_type="application/octet-stream",
        filename=artifact_path.name,
    )

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

@app.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (credentials.username,)
    ).fetchone()
    conn.close()

    if user is None or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token(username=credentials.username)
    return LoginResponse(access_token=token)

@app.get("/report/csv")
def report_csv(
    username: str = None,
    task_type: str = None,
    state: str = None,
    client_name: str = Depends(verify_token),
):
    rows = query_task_logs(username=username, task_type=task_type, state=state)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "task_id", "username", "ip_address", "task_type",
                    "submitted_at", "state", "stderr", "execution_time_sec"],
    )
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=task_report.csv"},
    )

@app.get("/report/pdf")
def report_pdf(
    username: str = None,
    task_type: str = None,
    state: str = None,
    client_name: str = Depends(verify_token),
):
    rows = query_task_logs(username=username, task_type=task_type, state=state)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    title = "Task Execution Report"
    filters_desc = []
    if username:
        filters_desc.append(f"user={username}")
    if task_type:
        filters_desc.append(f"type={task_type}")
    if state:
        filters_desc.append(f"state={state}")
    subtitle = f"Filters: {', '.join(filters_desc)}" if filters_desc else "All records"

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Paragraph(subtitle, styles["Normal"]))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Table header + rows
    table_data = [["ID", "User", "IP", "Type", "Submitted At", "State", "Time (s)"]]
    for r in rows:
        table_data.append([
            str(r["id"]),
            r["username"],
            r["ip_address"],
            r["task_type"],
            r["submitted_at"][:19],  # trim to readable length
            r["state"] or "-",
            str(r["execution_time_sec"]) if r["execution_time_sec"] else "-",
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1C7293")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=task_report.pdf"},
    )
