## Table of Contents

1. [Overview](#overview)
2. [System Design](#system-design)
3. [Architecture & Separation of Concerns](#architecture--separation-of-concerns)
4. [Overall Architecture](#21-overall-architecture)
5. [Main Components & Responsibilities](#22-main-components--their-responsibilities)
6. [End-to-End Data Flow](#23-end-to-end-data-flow)
7. [Data Pipeline & Runtime Execution](#data-flow-data-pipeline--runtime-execution)
8. [Learning Logic (Re-Ranking & Personalization)](#learning-logic-re-ranking--personalization)
9. [AI Usage](#ai-usage)
10. [Sample Dataset](#sample-dataset)
11. [Setup & Run Instructions](#setup--run-instructions)
12. [Data Ingestion, Search & Events](#data-ingestion-search--events)
13. [Frontend (Streamlit UI)](#frontend-streamlit-ui)
    
# Contextual Product Search System

## Overview

This project implements a production-oriented backend system for contextual product search.  
It combines semantic search, structured filtering, asynchronous event processing, and learning-based ranking to return relevant and explainable search results.

---

## System Design

The system follows a layered architecture with clear separation of concerns:
- **Frontend Layer** → Streamlit-based search and interaction UI (frontend.py)
- **API Layer** → FastAPI (main.py)  
- **Service Layer** → Ingestion, Search, Ranking logic  
- **Data Layer** → SQLite + SQLAlchemy (database.py, models.py)  
- **AI Layer** → Embeddings, Semantic Search, LLM explanations  
- **Event Layer** → Redis Streams (async behavior tracking)

---

## Architecture & Separation of Concerns

| Layer | Responsibility | Files |
|------|---------------|-------|
| API | Exposes endpoints, request validation | main.py |
| Ingestion | Product ingestion & embedding | ingest.py |
| Search | Semantic + filtered + ranked search | search.py |
| Data | Structured storage & learning signals | database.py, models.py |
| Vector DB | Semantic similarity search | vector_store.py |
| Events | Async user behavior tracking | event_consumer.py |
| AI Explainability | “Why this result?” | llm_explainer.py |
| UI (demo) | Search & interaction demo | frontend.py |

---

## 2.1 Overall Architecture

The system follows a layered backend architecture designed to clearly separate responsibilities and allow independent scaling of components.
![Alt text](https://github.com/ttaannnyyya/contextual_search/blob/main/architecture.png)

**Architecture flow:**

This structure ensures that:
- APIs remain thin and stateless  
- Business logic is centralized and reusable  
- Storage and AI components can evolve independently  

---

## 2.2 Main Components & Their Responsibilities
### 1. Frontend Layer (Streamlit UI)

**File:** `frontend.py`

- Provides a user interface for product search  
- Displays product details and ranking explanations  
- Allows user interactions such as click, add-to-cart, and purchase  

The frontend enables end-to-end testing of search, ranking, and event tracking through an interactive UI.

---

### 2. API Layer (FastAPI)

**File:** main.py

- Exposes REST endpoints for ingestion, search, and event tracking  
- Handles request validation and response formatting  
- Publishes user events asynchronously to Redis  

The API layer does not perform heavy computation, ensuring low latency and scalability.

---

### 3. Service Layer (Core Logic)

**Files:** ingest.py, search.py, event_consumer.py

- ingest.py implements a reusable, batch-based ingestion pipeline  
- search.py implements semantic retrieval, intent extraction, filtering, and re-ranking  
- event_consumer.py processes user behavior events and updates learning signals  

This layer contains the core intelligence of the system and can be extended without changing API contracts.

---

### 4. Data Layer (Persistent Storage)

**Files:** database.py, models.py, vector_store.py

- SQL database stores structured product data and behavioral counters  
- FAISS vector store handles high-dimensional semantic search  
- Redis acts as an event buffer and decouples analytics from request handling  

This separation avoids overloading a single datastore and mirrors real production search systems.

---
### 5. Event Layer (Asynchronous Tracking)

**File:** `event_consumer.py`

- Handles asynchronous user behavior tracking (click, add-to-cart, purchase)  
- Uses **Redis Streams (Memurai)** as a message queue  

The event layer ensures user interactions are recorded without impacting API latency and supports learning-based ranking.

---

### 6. AI / ML Layer

**Files:** ingest.py, search.py, llm_explainer.py

- Sentence-transformer model generates embeddings for products and queries  
- LLM generates explainable, human-readable ranking explanations  
- Same embedding model is used at ingestion and query time to maintain semantic consistency  

---

## 2.3 End-to-End Data Flow

### A. Product Ingestion Flow

```
CSV / JSON File
↓
Ingestion API (/ingest)
↓
Batch Processing & Normalization
↓
SQL DB (structured fields)
↓
Embedding Generation
↓
FAISS Vector Store
```

This flow ensures ingestion is:
- Reusable  
- Scalable to large catalogs  
- Consistent between structured and semantic storage  

---

### B. Search & Ranking Flow

```
User Query
↓
Query Embedding
↓
Semantic Retrieval (FAISS)
↓
Intent Extraction (price, brand, rating, etc.)
↓
SQL Filtering
↓
Behavior-aware Re-ranking
↓
LLM Explanation Generation
↓
Search Response
```

This staged approach avoids premature filtering and preserves semantic relevance.

---

### C. User Event Flow (Asynchronous)

```
User Action (click / cart / purchase)
↓
/event API
↓
Redis Stream (non-blocking)
↓
Event Consumer Service
↓
Behavior Counters Updated in DB
```

This ensures that user analytics never block the main search experience.

---

## 2.4 Key Technology Choices & Rationale

- **FastAPI:** Async-friendly, clean API design, production-ready  
- **SQLite:** Lightweight and can be easily swappable with Postgres/MySQL  
- **FAISS:** Fast, in-memory semantic similarity search  
- **Redis Streams:** Asynchronous, scalable event ingestion  
- **Sentence Transformers:** Efficient semantic embeddings for search  
- **LLM (via OpenRouter):** Explainable AI for transparent ranking decisions  

Each technology was chosen to demonstrate system-level thinking, not just correctness.

---

## Data Flow (Data Pipeline & Runtime Execution)

This section explains how data moves through the system at runtime, component by component.  
This section focuses on actual execution flow using the implemented files.

---

## 1. Product Ingestion Data Flow

**Entry Point:** main.py → POST /ingest

### 1. API Orchestration (main.py)

- Product ingestion starts when a CSV file is uploaded to the /ingest endpoint.  
- main.py acts only as a controller/orchestrator and does not contain ingestion logic.  
- The uploaded file stream is passed directly to the ingestion pipeline.  

### 2. Reusable Ingestion Pipeline (ingest.py)

- The ingest_csv() function processes the file in batches (chunked reading) to support large product catalogs.  
- For each product record:
  - Fields are normalized (title, description, category, brand, price, size, color, rating).  
  - Duplicate products are skipped using product_id checks.  
- Textual fields are combined to generate a semantic embedding for search.  

### 3. Structured Data Storage (database.py, models.py)

- Normalized product data is persisted in the SQL database.  
- database.py manages database connections and sessions.  
- models.py defines the Product table which stores:
  - Structured attributes used for filtering  
  - Behavioral counters (clicks, add-to-cart, purchases) used for learning-based ranking  

### 4. Semantic Indexing (vector_store.py)

- Generated embeddings are stored in a FAISS index.  
- A mapping between FAISS index positions and product_id is maintained.  
- This enables fast semantic similarity search independent of the relational database.  

**Outcome:**

Each product is indexed in two complementary forms:
- Structured SQL storage for filtering and analytics  
- Vector storage for semantic search  

---

## 2. Search & Ranking Data Flow

**Entry Point:** main.py → GET /search

### 1. Query Handling (main.py)

- Receives a natural language search query from the client.  
- Delegates the entire retrieval and ranking process to the search service.  

### 2. Semantic Retrieval (search.py)

- The query is converted into an embedding using the same model as ingestion.  
- FAISS is queried with over-fetching to avoid early loss of relevant products.  

### 3. Intent Extraction & Filtering (search.py)

- Explicit user intent is extracted from the query (price, brand, size, color, rating).  
- Filters are applied after semantic retrieval, preserving relevance while enforcing constraints.  

### 4. Learning-aware Re-ranking (search.py)

- Behavioral signals (clicks, add-to-cart, purchases) are normalized.  
- A final ranking score is computed by combining:
  - Semantic relevance  
  - Conversion signals  
  - Bounce penalties  
- Results are sorted by this final score.  

---

## 3. Asynchronous User Event Data Flow

User interaction tracking is implemented asynchronously and is fully decoupled from search execution.

### Event Publishing

#### 1. Event Capture (main.py)

- User actions (click, add-to-cart, purchase) are sent to the /event endpoint.  
- Events are immediately pushed to a Redis Stream.  
- The API responds without waiting for database updates.  

#### 2. Message Queue (Redis via Memurai)

- Redis is run locally using Memurai (Redis-compatible service for Windows).  
- Memurai must be kept running separately for the message queue to function.  
- This ensures user-facing APIs remain non-blocking.  

### Event Consumption

#### 3. Event Consumer (event_consumer.py)

- Runs as a separate, long-running background service.  
- Consumes events in batches from the Redis stream.  
- Updates corresponding behavioral counters in the database.  

#### 4. Persistent Learning Signals (models.py)

- Updated counters are stored in the Product table.  
- These signals directly influence future ranking decisions.  

**Outcome:**
- Event ingestion is asynchronous  
- API latency remains low  
- Search ranking improves over time using real user behavior  

---

## Learning Logic (Re-Ranking & Personalization)

The system uses a hybrid ranking approach that combines semantic relevance with user behavior signals.

### 1. Initial Ranking (Cold Start)

- Search results are initially ranked purely by semantic similarity.  
- The query embedding is compared with product embeddings created from:
  (title + description + category).  
- This ensures relevance even when there is no user interaction data.  

### 2. User Behavior Tracking

User actions are continuously tracked:
- Click  
- Add to Cart  
- Purchase  
- Bounce (negative signal)  

These signals are normalized to avoid bias toward popular products.

### 3. Re-Ranking Formula

```
final_score = (
0.55 * semantic_score
+ 0.20 * norm_buy
+ 0.15 * norm_cart
+ 0.10 * norm_click
- 0.10 * norm_bounce
)
```

**Design rationale:**
- Semantic relevance (55%) has the highest weight to preserve query intent.  
- Purchase has more weight than add-to-cart and click as it reflects stronger intent.  
- Bounce rate is penalized to push down irrelevant or misleading products.  

### 4. Learning Over Time

- Initially, rankings depend almost entirely on semantic score.  
- As user interactions increase, behavioral signals gradually influence ranking.  
- This allows the system to self-improve without retraining a model.  

### 5. Filtering Logic

- Hard filters (price range, category, availability) are applied at the database level.  
- Soft filters (semantic relevance) are applied during re-ranking.  

This design balances relevance, learning, and stability, making the system scalable and explainable.

---

## AI Usage

The system uses AI in two focused and explainable places:
1. Semantic Search (Retrieval)  
2. LLM-based Explanation Generation (Explainability)  

---

## 1. Semantic Search (Core Retrieval)

**Model:** all-MiniLM-L6-v2  
**Library:** Sentence Transformers  

- This model is used to generate dense vector embeddings for:
  - User search queries  
  - Product data: (title + description + category)  
- Both query and products are embedded into the same vector space, and similarity is computed using cosine similarity.  
- This enables meaning-based retrieval, not exact keyword matching.  

**Why this model?**
- Lightweight and fast (low latency)  
- Good semantic understanding for short e-commerce queries  
- Suitable for production without GPU dependency  

**Role in the system:**
- Provides the primary ranking signal  
- Handles synonyms, paraphrases, and intent-based matching  
- Works even when no user behavior data exists (cold start)  

---

## 2. LLM-based Explanation Generation (Explainability Layer)

**Model:** mistralai/mistral-7b-instruct  
**Platform:** OpenRouter (API-based)  

This LLM is not used for ranking.  
It is used only to explain why a product appeared in the search results.

**How it works:**
- After final re-ranking, the top products are passed to the LLM.  
- The model receives:
  - User query  
  - Product attributes (price, rating, category)  
  - Individual ranking signals (semantic score, click, cart, purchase)  

The LLM generates a 1–2 sentence factual explanation describing the most influential reason for ranking.

**Prompt design highlights:**
- Explicit instruction to:
  - Use only provided data  
  - Mention the most influential score  
  - Avoid hallucinations  
- temperature = 0 ensures deterministic, stable output  
- Token limit is kept low for cost and latency control  

**Why Mistral-7B?**
- Strong instruction-following ability  
- Fast and cost-efficient via OpenRouter  
- Suitable for short, grounded explanations  
- No fine-tuning required  

---

## 3. Separation of Concerns (Important Design Choice)

- Semantic model → Retrieval & ranking  
- LLM → Human-readable explanation only  

---

## Sample Dataset

The project uses a synthetically generated dataset to simulate a realistic e-commerce product catalog.
- **Dataset File**- products_final_clean.csv
- **Categories:** Shoes, Glasses, Electronics, Watches, Sportswear, Accessories, Footwear  
- **Brands:**  
  Nike, Adidas, Puma, Reebok, Skechers, Lenskart, RayBan, Titan, Fastrack, Boat, Sony, JBL, Samsung, Casio, Fossil, Apple, HRX, Wildcraft, Skybags, American Tourister, Bata, Woodland, RedTape, Campus  
- **Colors:** Black, White, Blue, Red, Grey, Green, Brown, Yellow  
- **Sizes:**  
  - Shoes: 6–11  
  - Clothing: XS, S, M, L, XL  
  - General: Small, Medium, Large  

For best results, please use search queries that are aligned with the listed categories, brands, or attributes, as the sample dataset is intentionally focused on this domain for demonstration purposes.

---

## Setup & Run Instructions

### 1. Clone the Repository

```
git clone https://github.com/ttaannnyyya/contextual_search.git
cd contextual_search
```

---

### 2. Create & Activate Virtual Environment (Recommended)

```
python -m venv venv
```

**Windows:**
```
venv\Scripts\activate
```

---

### 3. Install Dependencies

```
pip install -r requirements.txt
```

---

### 4. Environment Variables

Create a `.env` file in the project root and add:

```
OPENROUTER_API_KEY=your_openrouter_api_key
```

---

### 5. Start Redis (Memurai)

This project uses Memurai (Redis-compatible) on Windows.  
Ensure Memurai is running on:

```
localhost:6379
```

Memurai must remain running while the application is active.

---

### 6. Start Event Consumer (Required)

Open a separate terminal and run:

```
python event_consumer.py
```

- Runs continuously  
- Processes user events asynchronously (click, add-to-cart, purchase)  
- Updates Redis and syncs aggregated signals to the database  
- Required for learning-based re-ranking  

---

### 7. Run Backend API

Open another terminal:

```
uvicorn main:app --port 8002
```

- Starts the FastAPI backend  
- Handles search, ranking, filtering, and explanation APIs  

**Swagger UI (API Documentation):**  
http://127.0.0.1:8002/docs

---

### 8. Run Frontend

Open a new terminal:

```
streamlit run frontend.py
```

- Launches the Streamlit-based search UI  
- Enables user interaction and event generation  

---

## Data Ingestion, Search & Events

### Product Ingestion

- Product data must be ingested using the POST ingestion API available via Swagger UI:  
  http://127.0.0.1:8002/docs  
- This step is required before performing search or event tracking.  

---

### Search API

- Search requests can be submitted via the search API in Swagger UI.  
- The search response includes:
  - Product details  
  - Normalized behavioral scores (click, add-to-cart, purchase, bounce)  
  - Semantic similarity score  
  - Final score used for ranking  

This helps in debugging, transparency, and understanding ranking decisions.

---

### Event API

- User interaction events can be submitted via the event API:
  - click  
  - add_to_cart  
  - purchase  
- Events can be submitted for any product ID.  
- These events are processed asynchronously and influence future rankings.  

---

## Frontend (Streamlit UI)

All the above operations can also be performed using the Streamlit frontend:

- Search results display:
  - Product details  
  - Ranking explanation (why the product was shown)  
- Interactive buttons are available for:
  - Click  
  - Add to Cart  
  - Purchase  
- User actions are captured as events and persisted to the database via the event consumer.
  
