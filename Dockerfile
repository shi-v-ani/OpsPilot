FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY services ./services

ARG SERVICE_MODULE
ENV SERVICE_MODULE=${SERVICE_MODULE}

EXPOSE 8000

CMD ["sh", "-c", "uvicorn ${SERVICE_MODULE} --host 0.0.0.0 --port 8000"]
