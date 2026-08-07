"""
General-purpose script submitter — point this at any .py file
and it runs on the remote server, sandboxed, and prints the result.

Usage:
    python run_script.py path/to/your_script.py
"""

import sys
import time

import requests

SERVER_URL = "http://localhost:8000"
API_KEY = "key-client-alpha"


def submit_and_run(file_path: str, task_type: str = "general", client_id: str = "user-client"):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    print(f"Submitting '{file_path}'...")
    submit_resp = requests.post(
        f"{SERVER_URL}/submit-task",
        json={"task_type": task_type, "payload": code, "client_id": client_id},
        headers={"X-API-Key": API_KEY},
    )
    submit_resp.raise_for_status()
    task_id = submit_resp.json()["task_id"]
    print(f"Queued (task_id={task_id})")

    start = time.time()
    while True:
        poll_resp = requests.get(
            f"{SERVER_URL}/task-result/{task_id}",
            headers={"X-API-Key": API_KEY},
        )
        poll_resp.raise_for_status()
        data = poll_resp.json()

        if data["state"] != "PENDING":
            elapsed = time.time() - start
            result = data["result"]
            print(f"\nDone in {elapsed:.2f}s — state: {data['state']}")
            print("--- OUTPUT ---")
            print(result.get("stdout", "").strip() or "(no output)")
            if result.get("stderr"):
                print("--- ERRORS ---")
                print(result["stderr"].strip())
            return data

        time.sleep(0.5)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_script.py path/to/your_script.py [task_type]")
        print("  task_type options: general (default), numeric, ml, render")
        sys.exit(1)

    script_path = sys.argv[1]
    chosen_type = sys.argv[2] if len(sys.argv) > 2 else "general"

    submit_and_run(script_path, task_type=chosen_type)