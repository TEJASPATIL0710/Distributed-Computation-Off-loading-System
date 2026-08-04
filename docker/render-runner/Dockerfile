FROM python:3.13-slim

# ffmpeg isn't a Python package — it's a system tool, installed via apt
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /task
CMD ["python", "/task/script.py"]