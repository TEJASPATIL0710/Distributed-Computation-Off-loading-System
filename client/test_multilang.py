import requests

SERVER_URL = "http://localhost:8000"
USERNAME = "tejas"
PASSWORD = "mypassword123"

token = requests.post(f"{SERVER_URL}/login", json={"username": USERNAME, "password": PASSWORD}).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}


def run(language, code):
    resp = requests.post(
        f"{SERVER_URL}/submit-task",
        json={"task_type": "multilang", "payload": code, "language": language, "client_id": "lang-test"},
        headers=headers,
    )
    task_id = resp.json()["task_id"]
    print(f"[{language}] submitted, task_id={task_id}")

    import time
    while True:
        poll = requests.get(f"{SERVER_URL}/task-result/{task_id}", headers=headers)
        data = poll.json()
        if data["state"] != "PENDING":
            print(f"[{language}] state={data['state']}")
            print(data["result"]["stdout"])
            if data["result"]["stderr"]:
                print("STDERR:", data["result"]["stderr"])
            return
        time.sleep(1)


run("python", "print('Hello from Python')")
run("javascript", "console.log('Hello from JavaScript');")
run("cpp", '#include <iostream>\nint main() { std::cout << "Hello from C++" << std::endl; return 0; }')