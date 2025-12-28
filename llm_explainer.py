import os
from dotenv import load_dotenv
from openai import OpenAI

# Load env variables
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def generate_llm_explanation(query: str, product: dict) -> str:
    """
    Generates a short explanation (1–2 sentences) explaining
    why a product was shown for a user query using OpenRouter.
    """

    prompt = f"""
You are a precise product ranking explanation assistant.

User query:
"{query}"

Product details:
Brand: {product['brand']}
Category: {product['category']}
Price: ₹{product['price']}
Rating: {product['rating']}
Semantic score: {product.get('semantic_score')}
Click score: {product.get('norm_click')}
Add-to-cart score: {product.get('norm_cart')}
Purchase score: {product.get('norm_buy')}

Explain in 1–2 concise sentences why this product matches the query.
Mention the most influential score.
Use only the given information.
"""

    response = client.chat.completions.create(
        model="mistralai/mistral-7b-instruct",
        messages=[
            {
                "role": "system",
                "content": "You explain why a product appears in search results in a clear, factual manner."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=120
    )

    return response.choices[0].message.content.strip()
