FROM python:3.12-slim

RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.14.1 scikit-learn==1.3.2 pandas==2.1.3

WORKDIR /task
CMD ["python", "/task/script.py"]