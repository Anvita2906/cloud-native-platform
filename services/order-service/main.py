from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
import httpx
import os
from typing import Optional

app = FastAPI(title="Order Service")

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8000")

# Prometheus metrics
REQUEST_COUNT = Counter('order_service_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('order_service_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
EXTERNAL_CALL_COUNT = Counter('order_service_external_calls_total', 'External service calls', ['service', 'status'])

class Order(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    status: str

orders_db = [
    {"id": 1, "user_id": 1, "product_id": 101, "quantity": 2, "status": "completed"},
    {"id": 2, "user_id": 2, "product_id": 102, "quantity": 1, "status": "pending"},
]

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(duration)
    
    return response

@app.get("/")
def read_root():
    return {"service": "order-service", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/orders")
def get_orders():
    return {"orders": orders_db}

@app.get("/orders/{order_id}")
async def get_order_details(order_id: int):
    order = next((o for o in orders_db if o["id"] == order_id), None)
    if not order:
        return {"error": "Order not found"}, 404
    
    async with httpx.AsyncClient() as client:
        try:
            user_response = await client.get(f"{USER_SERVICE_URL}/users/{order['user_id']}")
            EXTERNAL_CALL_COUNT.labels(service="user-service", status=user_response.status_code).inc()
            
            product_response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{order['product_id']}")
            EXTERNAL_CALL_COUNT.labels(service="product-service", status=product_response.status_code).inc()
            
            order_details = order.copy()
            if user_response.status_code == 200:
                order_details["user"] = user_response.json()
            if product_response.status_code == 200:
                order_details["product"] = product_response.json()
            
            return order_details
        except Exception as e:
            EXTERNAL_CALL_COUNT.labels(service="error", status=0).inc()
            return {"order": order, "error": f"Failed to fetch details: {str(e)}"}
