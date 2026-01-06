from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

app = FastAPI(title="Product Service")

# Prometheus metrics
REQUEST_COUNT = Counter('product_service_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('product_service_request_duration_seconds', 'Request latency', ['method', 'endpoint'])
PRODUCT_STOCK = Gauge('product_service_stock_level', 'Product stock levels', ['product_id', 'product_name'])

class Product(BaseModel):
    id: int
    name: str
    price: float
    stock: int

products_db = [
    {"id": 101, "name": "Laptop", "price": 999.99, "stock": 50},
    {"id": 102, "name": "Mouse", "price": 29.99, "stock": 200},
    {"id": 103, "name": "Keyboard", "price": 79.99, "stock": 150},
]

# Initialize stock gauges
for product in products_db:
    PRODUCT_STOCK.labels(product_id=str(product["id"]), product_name=product["name"]).set(product["stock"])

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
    return {"service": "product-service", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/products")
def get_products():
    return {"products": products_db}

@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = next((p for p in products_db if p["id"] == product_id), None)
    if product:
        return product
    return {"error": "Product not found"}, 404
