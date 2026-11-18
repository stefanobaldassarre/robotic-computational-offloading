FROM python:3.13.15-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY task_a_server.py .
COPY image_processing.py .

EXPOSE 5001

CMD ["python", "task_a_server.py"]
