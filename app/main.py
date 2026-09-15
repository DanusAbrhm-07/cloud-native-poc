import os
import time
from fastapi import FastAPI, HTTPException
import redis

app = FastAPI(title="Cloud-Native PoC API", version="1.0.0")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Initialize Redis client with connection pooling
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@app.get("/health")
def health_check():
    start_time = time.time()
    try:
        redis_client.ping()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    latency = (time.time() - start_time) * 1000
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "ping_latency_ms": round(latency, 2)
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to the Modern Cloud-Native Development PoC!", "docs": "/docs"}

@app.post("/items/{item_id}")
def set_item(item_id: str, value: str):
    try:
        redis_client.set(item_id, value)
        return {"item_id": item_id, "value": value, "status": "stored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/items/{item_id}")
def get_item(item_id: str):
    try:
        value = redis_client.get(item_id)
        if value is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"item_id": item_id, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
