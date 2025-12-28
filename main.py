

# main.py
# --------
# Entry point of the FastAPI application.
# This file initializes the API, connects the database,
# creates tables, and exposes the ingestion endpoint.

from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from llm_explainer import generate_llm_explanation

import redis

from database import engine, SessionLocal
from models import Base
from ingest import ingest_csv
from search import semantic_search


# -------------------- APP INIT --------------------

# Create FastAPI app instance
app = FastAPI(title="Contextual Search API")

# Create all tables defined in models.py
# This runs once when the app starts
Base.metadata.create_all(bind=engine)


# -------------------- REDIS INIT (NEW) --------------------

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

EVENT_STREAM = "user_events"


# -------------------- EVENT SCHEMA (NEW) --------------------

class EventType(str, Enum):
    search = "search"
    click = "click"
    add_to_cart = "add_to_cart"
    purchase = "purchase"


class EventRequest(BaseModel):
    event_type: EventType
    query: str | None = None
    product_id: str | None = None


# -------------------- HEALTH CHECK --------------------

@app.get("/")
def root():
    """
    Health check endpoint.
    Used to verify that the API is running.
    """
    return {"status": "API running"}


# -------------------- INGESTION --------------------

@app.post("/ingest")
def ingest_products(file: UploadFile):
    """
    Ingest products from a CSV file.
    This endpoint triggers the reusable ingestion pipeline.
    """
    db = SessionLocal()
    ingest_csv(file.file, db)
    db.close()
    return {"status": "Products ingested successfully"}


# -------------------- SEARCH --------------------

@app.get("/search")
def search_products(query: str):
    """
    Search products using semantic similarity + filters.
    """
    db = SessionLocal()
    results = semantic_search(db, query)
    db.close()



    return [
        {
            "product_id": r["product"].product_id,
            "title": r["product"].title,
            "category": r["product"].category,
            "brand": r["product"].brand,
            "price": r["product"].price,
            "size": r["product"].size,
            "color": r["product"].color,
            "rating": r["product"].rating,

            # 👇 DEBUG / EXPLAINABILITY
            "semantic_score": r["semantic_score"],
            "normalized_click_score": r["norm_click"],
            "normalized_add_to_cart_score": r["norm_cart"],
            "normalized_purchase_score": r["norm_buy"],
            "bounce_penalty": r["norm_bounce"],
            "final_score": r["final_score"],
            # ✅LLM-generated explanation
            "explanation": generate_llm_explanation(
                query,
                {
                    "brand": r["product"].brand,
                    "category": r["product"].category,
                    "price": r["product"].price,
                    "rating": r["product"].rating,
                    "semantic_score": r["semantic_score"],
                    "norm_click": r["norm_click"],
                    "norm_cart": r["norm_cart"],
                    "norm_buy": r["norm_buy"],
                }
            )
        }
        for r in results
    ]


# -------------------- ASYNC EVENT TRACKING (NEW) --------------------

@app.post("/event")
def track_event(event: EventRequest):
    """
    Asynchronous user event tracking using Redis Streams
    """

    # Basic validation
    if event.event_type in ["click", "add_to_cart", "purchase"] and not event.product_id:
        return {"error": "product_id required for this event type"}

    payload = {
        "event_type": event.event_type,
        "query": event.query or "",
        "product_id": event.product_id or "",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Push event asynchronously to Redis stream
    redis_client.xadd(EVENT_STREAM, payload)

    return {"status": "event recorded"}

