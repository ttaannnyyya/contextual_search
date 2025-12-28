# vector_store.py
# ----------------
# This file manages the vector database using FAISS.
# It stores embeddings and allows semantic similarity search.

import faiss
import numpy as np

# Dimension of embeddings produced by all-MiniLM-L6-v2
EMBEDDING_DIM = 384

# FAISS index for similarity search (L2 distance)
index = faiss.IndexFlatL2(EMBEDDING_DIM)

# Mapping from FAISS index position → product_id
product_ids = []


def add_embedding(product_id, embedding):
    """
    Store a product embedding in the FAISS index.
    """
    vector = np.array([embedding]).astype("float32")
    index.add(vector)
    product_ids.append(product_id)



def search_embeddings(query_embedding, top_k=50):
    """
    Search FAISS index and return top_k product_ids with distances.
    """
    if index.ntotal == 0:
        return []

    vector = np.array([query_embedding]).astype("float32")
    distances, indices = index.search(vector, top_k)

    results = []
    for idx, dist in zip(indices[0], distances[0]):
        if idx < len(product_ids):
            results.append((product_ids[idx], float(dist)))
    return results
