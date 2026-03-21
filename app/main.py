from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime
import os
import platform

app = FastAPI(title="DevOps API", version="1.0.0")

# ---- Models ----
class Item(BaseModel):
    name: str
    value: str

# In-memory store (use Redis/DB in production)
store: dict = {}

# ---- Health endpoint (used by HEALTHCHECK and Kubernetes probes) ----
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("APP_ENV", "development"),
        "hostname": platform.node(),
        "python": platform.python_version(),
    }

# ---- Info endpoint ----
@app.get("/")
def root():
    return {
        "message": "DevOps API is running",
        "docs": "/docs",
        "health": "/health"
    }

# ---- CRUD endpoints ----
@app.get("/items")
def list_items():
    return {"items": store, "count": len(store)}

@app.post("/items/{key}")
def create_item(key: str, item: Item):
    store[key] = item.dict()
    return {"created": key, "data": store[key]}

@app.get("/items/{key}")
def get_item(key: str):
    if key not in store:
        raise HTTPException(status_code=404, detail=f"Item '{key}' not found")
    return {"key": key, "data": store[key]}

@app.delete("/items/{key}")
def delete_item(key: str):
    if key not in store:
        raise HTTPException(status_code=404, detail=f"Item '{key}' not found")
    deleted = store.pop(key)
    return {"deleted": key, "data": deleted}