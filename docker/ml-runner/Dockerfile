FROM python:3.12-slim

# CPU-only PyTorch build — much smaller than the default GPU-enabled wheel,
# and we have no GPU in this sandbox anyway.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir numpy==1.26.4

WORKDIR /task
CMD ["python", "/task/script.py"]
