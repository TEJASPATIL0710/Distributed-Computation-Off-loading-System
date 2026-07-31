FROM python:3.13-slim

# CPU-only PyTorch build — much smaller than the default GPU-enabled wheel,
# and we have no GPU in this sandbox anyway.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

WORKDIR /task
CMD ["python", "/task/script.py"]