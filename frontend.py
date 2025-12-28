import streamlit as st
import requests

API_URL = "http://localhost:8002"

st.set_page_config(page_title="Contextual Search", layout="wide")
st.title("🔍 Contextual Search Demo")

query = st.text_input(
    "Search products",
    placeholder="adidas red shoes under 3000 with 4 star rating"
)

# ---------------- STATE ----------------
if "results" not in st.session_state:
    st.session_state.results = None

# ---------------- SEARCH ----------------
if st.button("Search"):
    if not query.strip():
        st.warning("Enter a search query")
    else:
        try:
            res = requests.get(
                f"{API_URL}/search",
                params={"query": query},
                timeout=2000
            )
            if res.status_code == 200:
                st.session_state.results = res.json()
            else:
                st.error("Search failed")
        except Exception as e:
            st.error(f"Search API error: {e}")

# ---------------- RENDER RESULTS ----------------
results = st.session_state.results

if results:
    for p in results:
        st.subheader(p["title"])

        st.write(
            f"**Brand:** {p['brand']} | "
            f"**Price:** ₹{p['price']} | "
            f"⭐ **Rating:** {p['rating']}"
        )

        # AI explanation
        st.caption("🧠 Why this product was shown:")
        st.info(p.get("explanation", "Relevant to your search and popular with users"))

        col1, col2, col3 = st.columns(3)

        # ---------- CLICK ----------
        with col1:
            if st.button("Click", key=f"click_{p['product_id']}"):
                requests.post(
                    f"{API_URL}/event",
                    json={
                        "event_type": "click",
                        "product_id": p["product_id"],
                        "query": query
                    },
                    timeout=5
                )
                st.success("Click recorded")

        # ---------- ADD TO CART ----------
        with col2:
            if st.button("Add to Cart", key=f"cart_{p['product_id']}"):
                requests.post(
                    f"{API_URL}/event",
                    json={
                        "event_type": "add_to_cart",
                        "product_id": p["product_id"],
                        "query": query
                    },
                    timeout=5
                )
                st.success("Added to cart")

        # ---------- PURCHASE ----------
        with col3:
            if st.button("Buy", key=f"buy_{p['product_id']}"):
                requests.post(
                    f"{API_URL}/event",
                    json={
                        "event_type": "purchase",
                        "product_id": p["product_id"]
                    },
                    timeout=5
                )
                st.success("Purchase recorded")

        st.divider()
