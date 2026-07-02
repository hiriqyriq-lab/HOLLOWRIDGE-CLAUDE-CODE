FROM python:3.11-slim
WORKDIR /nil-agency
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY . .
CMD ["python3","orchestrator.py"]
