# ingest.py
# ----------
# Reusable ingestion pipeline for products.
# Accepts CSV data, normalizes fields, stores structured data in SQL,
# and generates vector embeddings for semantic search.

import pandas as pd
from sentence_transformers import SentenceTransformer
from models import Product
from vector_store import add_embedding

# Load embedding model once
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# The ingestion pipeline processes product data in batches,
# allowing it to scale to large catalogs without loading the entire
# dataset into memory.
def ingest_csv(file, db, batch_size=500):
    """
    Scalable ingestion pipeline:
    - Reads CSV in batches
    - Stores structured data in SQL
    - Generates embeddings
    - Stores embeddings in vector DB
    """

    # ✅ Fetch existing product_ids once
    existing_ids = {
        pid for (pid,) in db.query(Product.product_id).all()
    }

    # Read CSV in chunks (scalable for large datasets)
    for chunk in pd.read_csv(file, chunksize=batch_size):

        products_to_add = []

        for _, row in chunk.iterrows():
            pid = row["product_id"]

            # ✅ Skip if product already exists
            if pid in existing_ids:
                continue

            # Create Product object
            product = Product(
                product_id=pid,
                title=row["title"],
                description=row["description"],
                category=row["category"],
                brand=row.get("brand", ""),
                price=row["price"],
                size=row.get("size", ""),
                color=row.get("color", ""),
                rating=row.get("rating", 0)
            )

            products_to_add.append(product)
            existing_ids.add(pid)  # prevent duplicates in same upload

            # Text used for semantic embedding
            text = f"{row['title']} {row['description']} {row['brand']} {row['category']}"

            # Generate embedding
            embedding = embedding_model.encode(
                text,
                normalize_embeddings=True
            )

            # Store embedding in vector database
            add_embedding(pid, embedding)

        # Bulk insert for better performance
        if products_to_add:
            db.bulk_save_objects(products_to_add)
            db.commit()
