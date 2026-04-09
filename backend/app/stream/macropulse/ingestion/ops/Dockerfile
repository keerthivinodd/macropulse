FROM python:3.11-slim

WORKDIR /app

COPY app/stream/macropulse/ingestion/ops/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the ingestion package
COPY app/stream/macropulse/ingestion/ app/stream/macropulse/ingestion/

# Stub __init__.py files so Python package resolution works
# without pulling in the full backend agent/tool dependencies
RUN mkdir -p app/stream/macropulse app/stream app && \
    touch app/__init__.py app/stream/__init__.py app/stream/macropulse/__init__.py

CMD ["uvicorn", "app.stream.macropulse.ingestion.ops.api_main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
