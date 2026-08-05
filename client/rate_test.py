import requests

SERVER_URL = "http://localhost:8000"
API_KEY = "key-client-alpha"

for i in range(8):
    response = requests.post(
        f"{SERVER_URL}/submit-task",
        json={"task_type": "general", "payload": "print('hi')", "client_id": "rate-test"},
        headers={"X-API-Key": API_KEY},
    )
    print(f"Request {i+1}: status={response.status_code}")