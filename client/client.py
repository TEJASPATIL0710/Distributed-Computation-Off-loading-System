import time

import requests

SERVER_URL = "http://localhost:8000"


def submit_task(payload: str, task_type: str = "general", client_id: str = "client-1"):
    print(f"[{client_id}] Submitting task...")

    response = requests.post(
        f"{SERVER_URL}/submit-task",
        json={"task_type": task_type, "payload": payload, "client_id": client_id},
    )
    response.raise_for_status()
    submitted = response.json()
    task_id = submitted["task_id"]
    print(f"[{client_id}] Task queued, id={task_id}. Submission returned instantly — no blocking.")
    return task_id


def wait_for_result(task_id: str, client_id: str = "client-1", poll_interval: float = 0.5):
    print(f"[{client_id}] Polling for result...")
    start = time.time()

    while True:
        response = requests.get(f"{SERVER_URL}/task-result/{task_id}")
        response.raise_for_status()
        data = response.json()

        if data["state"] != "PENDING":
            elapsed = time.time() - start
            result = data["result"]
            print(f"[{client_id}] Done after {elapsed:.2f}s of polling")
            print(f"  state  : {data['state']}")
            print(f"  stdout : {result.get('stdout', '').strip()}")
            if result.get("stderr"):
                print(f"  stderr : {result['stderr'].strip()}")
            return data

        time.sleep(poll_interval)

if __name__ == "__main__":
    ml_script = (
        "import torch\n"
        "import torch.nn as nn\n"
        "\n"
        "model = nn.Sequential(nn.Linear(10, 32), nn.ReLU(), nn.Linear(32, 2))\n"
        "model.eval()\n"
        "\n"
        "dummy_input = torch.rand(1, 10)\n"
        "with torch.no_grad():\n"
        "    output = model(dummy_input)\n"
        "print(f'Inference output: {output.tolist()}')"
    )
    tid = submit_task(ml_script, task_type="ml")
    wait_for_result(tid)