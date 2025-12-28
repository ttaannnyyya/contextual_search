import re
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from models import Product
from vector_store import search_embeddings

# Same embedding model used during ingestion
# Ensures query and product vectors live in the same semantic space
model = SentenceTransformer("all-MiniLM-L6-v2")

# -------------------- HELPERS --------------------

def normalize_number(token: str) -> int:
    """
    Convert user-friendly numbers to raw values.
    Example: '10k' -> 10000, '5k' -> 5000
    """
    token = token.lower()
    if token.endswith("k"):
        return int(float(token[:-1]) * 1000)
    return int(token)


def min_max_norm(value, min_v, max_v):
    """
    Normalize behavioral signals to [0, 1]
    so they can be safely combined with semantic scores.
    """
    if max_v == min_v:
        return 0.0
    return (value - min_v) / (max_v - min_v)


def get_min_max_counts(db: Session):
    """
    Fetch min & max values of interaction signals
    Used for normalization during re-ranking.
    """
    stats = db.query(
        Product.click_count,
        Product.add_to_cart_count,
        Product.purchase_count
    ).all()

    clicks = [s[0] for s in stats]
    carts = [s[1] for s in stats]
    buys = [s[2] for s in stats]

    return {
        "click_min": min(clicks), "click_max": max(clicks),
        "cart_min": min(carts), "cart_max": max(carts),
        "buy_min": min(buys), "buy_max": max(buys),
    }

# -------------------- INTENT EXTRACTORS --------------------

def extract_price_range(query: str):
    """
    Extract explicit price intent from the query
    Example: 'under 5k', 'between 2k and 6k'
    """
    q = query.lower()

    # between X and Y
    match = re.search(r"between\s+(\d+\.?\d*k?)\s+and\s+(\d+\.?\d*k?)", q)
    if match:
        return normalize_number(match.group(1)), normalize_number(match.group(2))

    # under / below
    match = re.search(r"(under|below|less than)\s+(\d+\.?\d*k?)", q)
    if match:
        return None, normalize_number(match.group(2))

    # above / over
    match = re.search(r"(above|over|more than)\s+(\d+\.?\d*k?)", q)
    if match:
        return normalize_number(match.group(2)), None

    return None, None


def extract_size(query: str):
    """Extract size intent if explicitly mentioned"""
    match = re.search(r"size\s*(\w+)", query.lower())
    return match.group(1) if match else None


def extract_color(query: str):
    """Simple rule-based color detection"""
    colors = ["black", "white", "blue", "red", "grey"]
    for c in colors:
        if c in query.lower():
            return c
    return None


def extract_brand(query: str, db: Session):
    """
    Match brand names dynamically from DB
    Avoids hardcoding brand lists.
    """
    brands = [b[0].lower() for b in db.query(Product.brand).distinct()]
    for brand in brands:
        if brand and brand in query.lower():
            return brand
    return None


def extract_rating(query: str):
    """Extract rating intent like '4 star', 'above 4.5 rating'"""
    q = query.lower()

    match = re.search(r"(above|over|more than)\s+(\d(\.\d)?)\s*(star|rating)", q)
    if match:
        return float(match.group(2))

    match = re.search(r"(\d(\.\d)?)\s*(star|rating)", q)
    if match:
        return float(match.group(1))

    return None

# -------------------- SEMANTIC SEARCH + RE-RANKING --------------------

def semantic_search(db: Session, query: str, top_k: int = 10):
    """
    FINAL SEARCH FLOW
    -----------------
    1. Semantic retrieval (FAISS)
    2. Intent-aware structured filtering
    3. Learning-based re-ranking
    """

    # 1️⃣ Convert user query into embedding
    query_embedding = model.encode(query, normalize_embeddings=True)

    # 2️⃣ Over-fetch from FAISS to avoid early filtering loss
    FAISS_K = top_k * 5
    candidates = search_embeddings(query_embedding, top_k=FAISS_K)

    if not candidates:
        return []

    # Map product_id -> semantic distance
    distance_map = {pid: dist for pid, dist in candidates}
    product_ids = list(distance_map.keys())

    # 3️⃣ Extract user intent from natural language query
    brand = extract_brand(query, db)
    color = extract_color(query)
    size = extract_size(query)
    rating = extract_rating(query)
    min_price, max_price = extract_price_range(query)

    # 4️⃣ Apply structured filters AFTER semantic retrieval
    # This preserves relevance while respecting constraints
    q = db.query(Product).filter(Product.product_id.in_(product_ids))

    if brand:
        q = q.filter(Product.brand.ilike(f"%{brand}%"))

    if color:
        q = q.filter(Product.color.ilike(f"%{color}%"))

    if size:
        q = q.filter(Product.size == size)

    if min_price is not None:
        q = q.filter(Product.price >= min_price)

    if max_price is not None:
        q = q.filter(Product.price <= max_price)

    if rating is not None:
        q = q.filter(Product.rating >= rating)

    products = q.all()
    if not products:
        return []

    # 5️⃣ Fetch statistics for behavior-based normalization
    stats = get_min_max_counts(db)

    ranked_results = []

    for p in products:
        # Convert FAISS distance to similarity score
        distance = distance_map.get(p.product_id, 1.0)
        semantic_score = 1 / (1 + distance)

        # Normalize interaction signals
        norm_click = min_max_norm(
            p.click_count, stats["click_min"], stats["click_max"]
        )
        norm_cart = min_max_norm(
            p.add_to_cart_count, stats["cart_min"], stats["cart_max"]
        )
        norm_buy = min_max_norm(
            p.purchase_count, stats["buy_min"], stats["buy_max"]
        )

        # Approximate bounce as low-intent interaction
        bounce = max(
            p.click_count - p.add_to_cart_count - p.purchase_count, 0
        )
        norm_bounce = min_max_norm(
            bounce, stats["click_min"], stats["click_max"]
        )

        # Final ranking score combines relevance + behavior
        final_score = (
            0.55 * semantic_score
            + 0.20 * norm_buy
            + 0.15 * norm_cart
            + 0.10 * norm_click
            - 0.10 * norm_bounce
        )

        ranked_results.append(
            (
                final_score,
                {
                    "product": p,
                    "semantic_score": round(semantic_score, 4),
                    "norm_click": round(norm_click, 4),
                    "norm_cart": round(norm_cart, 4),
                    "norm_buy": round(norm_buy, 4),
                    "norm_bounce": round(norm_bounce, 4),
                }
            )
        )

    # Sort results by combined relevance score
    ranked_results.sort(key=lambda x: x[0], reverse=True)

    # Final top-k results returned to API
    return [
        {
            **item,
            "final_score": round(score, 4)
        }
        for score, item in ranked_results[:top_k]
    ]
