# Distributed-Computation-Off-loading-System
A multi-client, load-balanced platform that lets low-power devices offload heavy compute tasks to a remote server — securely, reliably, at scale.

# Compute Offload — Startup Commands

Run these in order. Each "Terminal X" is a separate terminal tab/window.

## One-time check (any terminal)
docker ps  
docker start redis-broker

## Terminal 1 — Worker 1
celery -A celery_app worker --loglevel=info --pool=solo -n worker1@%h

## Terminal 2 — Worker 2
celery -A celery_app worker --loglevel=info --pool=solo -n worker2@%h

## Terminal 3 — Worker 3
celery -A celery_app worker --loglevel=info --pool=solo -n worker3@%h

## Terminal 4 — FastAPI Server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

## Terminal 5 — Client (idle, ready for scripts)
cd client

## URLs once running
Login page:  http://localhost:8000/static/login.html  
Dashboard:   http://localhost:8000/dashboard  
API docs:    http://localhost:8000/docs

## ML and video rendering examples

Submit the included CPU-only ML inference example with:

    python client/run_script.py my_scripts/ml_inference_example.py ml

Submit the included FFmpeg render example with:

    python client/run_script.py my_scripts/render_example.sh render

The render result now includes an `artifacts` list. Each item contains a
`download_path` such as `/task-artifact/<task-id>/output.mp4`; request that
path with the same Bearer token to download the generated media.

## Occasional maintenance
Flush Redis (safe, doesn't touch database):  
docker exec -it redis-broker redis-cli FLUSHALL

Check logged tasks:  
python -c "from database import get_connection; conn = get_connection(); [print(dict(r)) for r in conn.execute('SELECT * FROM task_logs').fetchall()]"
