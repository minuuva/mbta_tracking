FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY mbta_client.py .
COPY dynamo.py .
COPY storage.py .
COPY app.py .

CMD ["python", "app.py"]