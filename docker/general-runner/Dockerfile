FROM python:3.13-slim

# No pip installs, no extra tools — keep the sandbox minimal.
# A smaller image means less attack surface and faster startup.

WORKDIR /task
CMD ["python", "/task/script.py"]