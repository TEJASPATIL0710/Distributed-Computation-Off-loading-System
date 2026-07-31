import time
import requests

SERVER_URL = "http://localhost:8000"

payload = "import time\ntime.sleep(8)\nprint('survived the whole 8 seconds')"

resp = requests.post(
    f"{SERVER_URL}/submit-task",
    json={"task_type": "general", "payload": payload, "client_id": "kill-test"},
)
task_id = resp.json()["task_id"]
print(f"Task submitted: {task_id}")
print("Now go kill one of the worker terminals within the next 8 seconds (Ctrl+C it).")

start = time.time()
while True:
    poll = requests.get(f"{SERVER_URL}/task-result/{task_id}")
    data = poll.json()
    if data["state"] != "PENDING":
        print(f"Final state: {data['state']} after {time.time()-start:.1f}s")
        print(f"Result: {data['result']}")
        break
    time.sleep(1)