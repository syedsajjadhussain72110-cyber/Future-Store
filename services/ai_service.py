"""
Future Store — AI Assistant Service
Powers the in-app chat widget (no external API key required, so it works
out of the box for every deployment of this project).

This is a lightweight retrieval + intent-matching assistant: it reads the
real product catalog from MongoDB and answers from that data (search,
category browsing, price lookups, stock, recommendations) plus a small
set of store-policy answers (shipping, returns, payment, contact). It
never invents a product, price, or policy that isn't actually in the
database or in the canned policy facts below, so its answers stay
truthful even though it isn't a general-purpose LLM.

Swap-in note: if a deployer wants real LLM-generated answers, the single
place to change is `answer()` — feed `user_message` plus the
`_catalog_context()` snippet to whatever model client is preferred and
return its text instead. Everything else (the route, the widget, the
session-based chat history) stays the same.
"""
import re

from services.image_utils import normalize_image

GREETING_WORDS = {"hi", "hello", "hey", "yo", "salam", "assalam", "good morning", "good evening", "good afternoon"}

THANKS_WORDS = {"thanks", "thank you", "thx", "appreciate it", "shukriya"}

POLICY_FACTS = {
    "shipping": (
        "Shipping is free on every order over $50. Orders under $50 ship for a flat "
        "small fee at checkout. Most orders arrive within 3-5 business days."
    ),
    "returns": (
        "You can return most items within 30 days of delivery for a full refund, as long "
        "as they're unused and in their original packaging. Visit the Returns page from "
        "the footer, or your Order History, to start a return."
    ),
    "payment": (
        "This academic prototype records demo orders only. The checkout payment "
        "options are interface examples; no card or wallet payment is processed."
    ),
    "contact": (
        "You can reach our support team anytime via the Contact page in the footer, "
        "or just keep chatting with me here for quick product questions."
    ),
    "account": (
        "You can create an account or sign in from the top-right of any page. "
        "Once signed in you'll have access to your cart, order history, and saved details."
    ),
}

CATEGORY_SYNONYMS = {
    "phone": "Electronics", "phones": "Electronics", "headphone": "Electronics",
    "headphones": "Electronics", "earbuds": "Electronics", "tv": "Electronics",
    "speaker": "Electronics", "electronics": "Electronics",
    "laptop": "Computers", "laptops": "Computers", "computer": "Computers",
    "computers": "Computers", "monitor": "Computers", "pc": "Computers",
    "clothes": "Clothing", "clothing": "Clothing", "shirt": "Clothing",
    "jacket": "Clothing", "fashion": "Clothing",
    "shoes": "Footwear", "sneakers": "Footwear", "footwear": "Footwear",
    "kitchen": "Kitchen", "cookware": "Kitchen",
    "garden": "Home & Garden", "home": "Home & Garden", "furniture": "Home & Garden",
    "sports": "Sports & Fitness", "fitness": "Sports & Fitness", "gym": "Sports & Fitness",
    "beauty": "Beauty", "makeup": "Beauty", "skincare": "Beauty",
    "toys": "Toys & Games", "games": "Toys & Games", "gaming": "Toys & Games",
    "books": "Books", "book": "Books",
    "watch": "Watches", "watches": "Watches",
    "baby": "Baby & Kids", "kids": "Baby & Kids",
    "pet": "Pet Supplies", "pets": "Pet Supplies", "dog": "Pet Supplies", "cat": "Pet Supplies",
    "grocery": "Grocery", "snacks": "Grocery",
}

PRICE_PATTERN = re.compile(r"under\s*\$?(\d+)|below\s*\$?(\d+)|less than\s*\$?(\d+)|\$?(\d+)\s*or less")


def _matched_category(text: str) -> str | None:
    text_lower = text.lower()
    for word, category in CATEGORY_SYNONYMS.items():
        if word in text_lower:
            return category
    return None


def _matched_price_ceiling(text: str):
    m = PRICE_PATTERN.search(text.lower())
    if not m:
        return None
    for group in m.groups():
        if group:
            return float(group)
    return None


def _matched_policy(text: str) -> str | None:
    text_lower = text.lower()
    if any(w in text_lower for w in ("ship", "delivery", "deliver")):
        return "shipping"
    if any(w in text_lower for w in ("return", "refund", "exchange")):
        return "returns"
    if any(w in text_lower for w in ("pay", "payment", "cod", "card", "easypaisa", "jazzcash")):
        return "payment"
    if any(w in text_lower for w in ("contact", "support", "human", "agent", "talk to someone")):
        return "contact"
    if any(w in text_lower for w in ("account", "sign in", "login", "log in", "register", "sign up")):
        return "account"
    return None


def _format_product_line(p: dict) -> str:
    return f"{p['name']} — ${p['price']:.2f} ({p.get('rating', 0):.1f}★)"


def answer(db, user_message: str, history: list | None = None) -> dict:
    """
    Return {"reply": str, "products": [product dicts with id/name/price/image]}
    for the given user_message. `history` (list of {"role","content"} dicts)
    is accepted for future use (multi-turn context) but the current
    intent-matching logic only needs the latest message.
    """
    text = (user_message or "").strip()
    text_lower = text.lower()

    if not text:
        return {"reply": "I didn't catch that — what are you looking for today?", "products": []}

    # ── greetings / thanks ──────────────────────────────────────────────────
    if any(text_lower == g or text_lower.startswith(g + " ") or text_lower.startswith(g + ",") for g in GREETING_WORDS):
        return {
            "reply": (
                "Hey! I'm the Future Store assistant. Ask me to find a product "
                "(\"show me headphones under $100\"), check shipping/returns, or "
                "anything else about your shopping experience."
            ),
            "products": [],
        }

    if any(w in text_lower for w in THANKS_WORDS):
        return {"reply": "Anytime! Let me know if there's anything else you need. 🙂", "products": []}

    # ── store policy questions ──────────────────────────────────────────────
    policy = _matched_policy(text)
    price_ceiling = _matched_price_ceiling(text)
    category = _matched_category(text)

    # If it's a pure policy question with no product intent, answer directly.
    if policy and not category and price_ceiling is None and not any(
        w in text_lower for w in ("show", "find", "search", "recommend", "looking for", "suggest")
    ):
        return {"reply": POLICY_FACTS[policy], "products": []}

    # ── product search: build a Mongo query from whatever we understood ────
    query: dict = {"is_active": 1}
    if category:
        query["category"] = category
    if price_ceiling is not None:
        query["price"] = {"$lte": price_ceiling}

    # Free-text fallback: also try matching the raw message against name/
    # description/brand if no category synonym was recognised, so brand or
    # product-name questions ("do you have Sony headphones?") still work.
    used_text_search = False
    if not category:
        # strip filler words, generic nouns, and punctuation before using
        # what's left as search terms — "do you have Sony products?"
        # should search for "sony", not the literal phrase "sony products?"
        cleaned = re.sub(PRICE_PATTERN, "", text_lower)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)  # strip punctuation
        cleaned = re.sub(
            r"\b(show me|find me|find|search for|search|looking for|i want|i need|"
            r"do you have|recommend|suggest|please|some|any|a|an|the|for|of|me|"
            r"products?|items?|stuff|things?|sell|got)\b",
            " ",
            cleaned,
        )
        words = [w for w in cleaned.split() if len(w) >= 3]

        if words:
            # Match any product whose name/description/brand contains ANY of
            # the remaining significant words (e.g. "sony" alone is enough),
            # rather than requiring the full original phrase verbatim.
            or_clauses = []
            for word in words:
                regex = {"$regex": re.escape(word), "$options": "i"}
                or_clauses.extend([{"name": regex}, {"description": regex}, {"brand": regex}])
            query["$or"] = or_clauses
            used_text_search = True

    if category or price_ceiling is not None or used_text_search:
        results = list(db.products.find(query).sort("rating", -1).limit(4))

        if results:
            lines = "\n".join(f"• {_format_product_line(p)}" for p in results)
            reply = f"Here's what I found:\n{lines}\n\nTap a card below to see details."
            products = [
                {"id": p["_id"], "name": p["name"], "price": p["price"], "image": normalize_image(p.get("image", ""))}
                for p in results
            ]
            return {"reply": reply, "products": products}
        else:
            return {
                "reply": (
                    "I couldn't find anything matching that. Try a different category "
                    "or a higher price range — or browse all products from the homepage."
                ),
                "products": [],
            }

    # ── nothing matched: graceful fallback ──────────────────────────────────
    return {
        "reply": (
            "I can help you find products, check prices, or answer questions about "
            "shipping, returns, and payment. Try something like \"recommend a gaming laptop\" "
            "or \"what's your return policy?\""
        ),
        "products": [],
    }
