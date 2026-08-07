"""
Module 5 — Multi-client load test

Fires off several tasks concurrently (simulating multiple clients),
then watches all of them complete. With 3 workers running, you should
see tasks finish in overlapping/parallel time, not strictly one-after-another.
"""

import threading
import time

import requests

SERVER_URL = "http://localhost:8000"


def submit_and_wait(client_id: str, payload: str, task_type: str, results: dict):
    start = time.time()

    submit_resp = requests.post(
        f"{SERVER_URL}/submit-task",
        json={"task_type": task_type, "payload": payload, "client_id": client_id},
        headers={"X-API-Key": "key-client-alpha"},
    )
    submit_resp.raise_for_status()
    task_id = submit_resp.json()["task_id"]
    print(f"[{client_id}] submitted (task_id={task_id[:8]}...)")

    while True:
        poll_resp = requests.get(f"{SERVER_URL}/task-result/{task_id}", headers={"X-API-Key": "key-client-alpha"})
        data = poll_resp.json()
        if data["state"] != "PENDING":
            elapsed = time.time() - start
            results[client_id] = {"state": data["state"], "elapsed": round(elapsed, 2)}
            print(f"[{client_id}] finished in {elapsed:.2f}s — state={data['state']}")
            return
        time.sleep(0.3)


if __name__ == "__main__":
    # 6 simulated clients, mixing task types, all fired at once.
    tasks = [
        ("client-A", "general", "import time\ntime.sleep(2)\nprint('A done')"),
        ("client-B", "general", "import time\ntime.sleep(2)\nprint('B done')"),
        ("client-C", "numeric", "import numpy as np\na=np.random.rand(300,300)\nprint((a@a).sum())"),
        ("client-D", "numeric", "import numpy as np\na=np.random.rand(300,300)\nprint((a@a).sum())"),
        ("client-E", "ml", "import torch\nm=torch.nn.Linear(10,2)\nprint(m(torch.rand(1,10)).tolist())"),
        ("client-F", "ml", "import torch\nm=torch.nn.Linear(10,2)\nprint(m(torch.rand(1,10)).tolist())"),
        ("client-G", "render", "ffmpeg -f lavfi -i testsrc=duration=2:size=160x120:rate=10 -c:v libx264 -y /task/output.mp4 2>&1 | tail -n 3\necho done"),
        ("client-H", "render", "ffmpeg -f lavfi -i testsrc=duration=2:size=160x120:rate=10 -c:v libx264 -y /task/output.mp4 2>&1 | tail -n 3\necho done"),
    ]

    results = {}
    threads = []
    overall_start = time.time()

    for client_id, task_type, script in tasks:
        t = threading.Thread(target=submit_and_wait, args=(client_id, script, task_type, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    total_elapsed = time.time() - overall_start
    print(f"\nAll {len(tasks)} tasks completed in {total_elapsed:.2f}s total (wall-clock)")
    print("If this were fully sequential on 1 worker, it would take roughly the sum of each task's own time instead.")