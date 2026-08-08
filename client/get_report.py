import requests

SERVER_URL = "http://localhost:8000"
USERNAME = "tejas"
PASSWORD = "mypassword123"

token = requests.post(f"{SERVER_URL}/login", json={"username": USERNAME, "password": PASSWORD}).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

csv_resp = requests.get(f"{SERVER_URL}/report/csv", headers=headers)
with open("task_report.csv", "wb") as f:
    f.write(csv_resp.content)
print(f"CSV saved: {len(csv_resp.content)} bytes")

pdf_resp = requests.get(f"{SERVER_URL}/report/pdf", headers=headers)
with open("task_report.pdf", "wb") as f:
    f.write(pdf_resp.content)
print(f"PDF saved: {len(pdf_resp.content)} bytes")