from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import httpx
import os
import logging
import json

# JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "user-service",
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }
        return json.dumps(log_obj)

logger = logging.getLogger("user-service")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

app = FastAPI(title="User Service")

# Prometheus metrics
REQUEST_COUNT = Counter('user_service_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('user_service_request_duration_seconds', 'Request latency', ['method', 'endpoint'])

class User(BaseModel):
    id: int
    name: str
    email: str

users_db = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
]

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)
    
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s")
    
    return response

@app.get("/")
def read_root():
    logger.info("Root endpoint called")
    return {"service": "user-service", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/users")
def get_users():
    logger.info("Fetching all users")
    return {"users": users_db}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    logger.info(f"Fetching user with id: {user_id}")
    user = next((u for u in users_db if u["id"] == user_id), None)
    if user:
        return user
    logger.warning(f"User not found: {user_id}")
    return {"error": "User not found"}, 404
