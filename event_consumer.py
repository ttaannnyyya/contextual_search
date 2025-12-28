from redis import Redis
from database import SessionLocal
from models import Product
from database import engine
from models import Base

# Ensure tables exist
Base.metadata.create_all(bind=engine)

"""
Event Consumer Service

This script runs continuously in the background to consume user interaction
events (click, add-to-cart, purchase) from Redis.

Each event is processed asynchronously and used to update corresponding
behavioral counters in the database (click_count, add_to_cart_count,
purchase_count).

Note:
This service must be running for user events to be persisted and for
search ranking to learn from real user behavior.
"""


# For local Windows development, Redis was run using Memurai (Redis-compatible service). In production, 
# Redis would run as a managed service or containerized deployment without code changes.
r = Redis(host="localhost", port=6379, decode_responses=True)

STREAM = "user_events"
GROUP = "analytics_group"
CONSUMER = "worker_1"

# Create consumer group (run once)
try:
    r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
except:
    pass


while True:
    messages = r.xreadgroup(
        GROUP,
        CONSUMER,
        {STREAM: ">"},
        count=10,
        block=2000
    )

    if not messages:
        continue

    db = SessionLocal()

    for _, events in messages:
        for msg_id, data in events:
            product_id = data.get("product_id")
            event_type = data.get("event_type")

            if not product_id:
                r.xack(STREAM, GROUP, msg_id)
                continue

            product = db.query(Product).filter_by(product_id=product_id).first()
            if not product:
                r.xack(STREAM, GROUP, msg_id)
                continue

            # Update counters when a event happens
            if event_type == "click":
                product.click_count += 1
            elif event_type == "add_to_cart":
                product.add_to_cart_count += 1
            elif event_type == "purchase":
                product.purchase_count += 1
            print(f"Processed event {event_type} for product {product_id}")

            r.xack(STREAM, GROUP, msg_id)

    db.commit()
    db.close()

