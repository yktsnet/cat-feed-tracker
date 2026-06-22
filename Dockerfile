FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ ./server/
COPY config/ ./config/

ENV PYTHONPATH=/app/server

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
