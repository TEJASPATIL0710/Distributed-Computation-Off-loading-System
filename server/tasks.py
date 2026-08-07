import os
import json
import subprocess
import tempfile
import time
import redis as redis_lib

from celery_app import celery_app

dashboard_redis = redis_lib.Redis(host="localhost", port=6379, db=1, decode_responses=True)

def mark_busy(hostname, task_name):
    dashboard_redis.set(
        f"worker_status:{hostname}",
        json.dumps({"busy": True, "task": task_name}),
        ex=60,  # auto-expires after 60s as a safety net, in case a worker dies without cleaning up
    )


def mark_idle(hostname):
    dashboard_redis.set(
        f"worker_status:{hostname}",
        json.dumps({"busy": False, "task": None}),
        ex=120,  # refreshed on every task completion; expires if a worker vanishes for 2+ min
    )

@celery_app.task(name="run_general_task", bind=True)
def run_general_task(self, payload: str):
    """
    This is the same Docker-sandboxed execution from Module 2 —
    just now running inside a Celery worker process instead of
    directly inside the FastAPI request handler.
    """
    start = time.time()

    mark_busy(self.request.hostname, "run_general_task")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(payload)
        script_path = f.name

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--memory", "256m",
                "--cpus", "0.5",
                "--network", "none",
                "-v", f"{script_path}:/task/script.py:ro",
                "offload-general-runner",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed = time.time() - start
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time_sec": round(elapsed, 4),
            "worker": self.request.hostname,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Task exceeded 15 second timeout.",
            "execution_time_sec": round(elapsed, 4),
        }
    finally:
        os.unlink(script_path)
        mark_idle(self.request.hostname)

@celery_app.task(name="run_numeric_task", bind=True)
def run_numeric_task(self, payload: str):
    """
    Same pattern as run_general_task, just pointed at the
    numeric-runner image instead of general-runner.
    """
    start = time.time()

    mark_busy(self.request.hostname, "run_numeric_task")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(payload)
        script_path = f.name

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--memory", "512m",       # a bit more headroom than general — matrix ops need it
                "--cpus", "1.0",
                "--network", "none",
                "-v", f"{script_path}:/task/script.py:ro",
                "offload-numeric-runner",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        elapsed = time.time() - start
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time_sec": round(elapsed, 4),
            "worker": self.request.hostname,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Task exceeded 20 second timeout.",
            "execution_time_sec": round(elapsed, 4),
        }
    finally:
        os.unlink(script_path)
        mark_idle(self.request.hostname)

@celery_app.task(name="run_ml_task", bind=True)
def run_ml_task(self, payload: str):
    """
    Same pattern again — only the image and resource limits differ.
    ML inference gets more memory/CPU headroom and a longer timeout
    since model loading + forward passes are heavier than plain scripts.
    """
    start = time.time()

    mark_busy(self.request.hostname, "run_ml_task")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(payload)
        script_path = f.name

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--memory", "1g",
                "--cpus", "1.0",
                "--network", "none",
                "-v", f"{script_path}:/task/script.py:ro",
                "offload-ml-runner",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed = time.time() - start
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time_sec": round(elapsed, 4),
            "worker": self.request.hostname,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Task exceeded 30 second timeout.",
            "execution_time_sec": round(elapsed, 4),
        }
    finally:
        os.unlink(script_path)
        mark_idle(self.request.hostname)

@celery_app.task(name="run_render_task", bind=True)
def run_render_task(self, payload: str):
    """
    Same pattern as the others. The 'payload' here is a shell command
    string (FFmpeg command), not Python code — since rendering tasks
    are naturally expressed as FFmpeg commands, not scripts.
    """
    start = time.time()

    mark_busy(self.request.hostname, "run_render_task")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, encoding="utf-8", newline="\n"
    ) as f:
        f.write(payload)
        script_path = f.name

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--memory", "512m",
                "--cpus", "1.0",
                "--network", "none",
                "-v", f"{script_path}:/task/script.sh:ro",
                "--entrypoint", "bash",
                "offload-render-runner",
                "/task/script.sh",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed = time.time() - start
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time_sec": round(elapsed, 4),
            "worker": self.request.hostname,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            "status": "error",
            "stdout": "",
            "stderr": "Task exceeded 30 second timeout.",
            "execution_time_sec": round(elapsed, 4),
        }
    finally:
        os.unlink(script_path)
        mark_idle(self.request.hostname)