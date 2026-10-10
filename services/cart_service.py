"""
Future Store — Cart Service (MongoDB)
All shopping-cart DB operations in one place.
"""
from app_db import next_id


# ─── read ─────────────────────────────────────────────────────────────────────

def get_cart_items(db, user_id: int) -> list:
    """
    Return cart documents joined with product data, matching the shape the
    templates expect: cart_id, quantity, id, name, price, image, brand, stock.

    Mongo has no implicit JOIN, so we fetch cart rows then batch-fetch the
    referenced products in a single query (avoids an N+1 query pattern).
    """
    cart_rows = list(db.cart.find({"user_id": user_id}))
    if not cart_rows:
        return []

    product_ids = {c["product_id"] for c in cart_rows}
    products = db.products.find({"_id": {"$in": list(product_ids)}})
    product_by_id = {p["_id"]: p for p in products}

    items = []
    for c in cart_rows:
        p = product_by_id.get(c["product_id"])
        if not p:
            continue  # product was deleted/deactivated since being added
        items.append({
            "cart_id":  c["_id"],
            "quantity": c["quantity"],
            "id":       p["_id"],
            "name":     p["name"],
            "price":    p["price"],
            "image":    p.get("image", ""),
            "brand":    p.get("brand", ""),
            "stock":    p.get("stock", 0),
        })
    return items


def get_cart_count(db, user_id: int) -> int:
    """Return the total number of items (sum of quantities) in the cart."""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$quantity"}}},
    ]
    result = list(db.cart.aggregate(pipeline))
    return int(result[0]["total"]) if result else 0


def get_cart_total(items: list) -> float:
    """Calculate subtotal from a list of cart item dicts."""
    return sum(item["price"] * item["quantity"] for item in items)


# ─── write ────────────────────────────────────────────────────────────────────

def add_to_cart(db, user_id: int, product_id: int, quantity: int = 1) -> None:
    """Add a product to cart, or increment quantity if already present."""
    existing = db.cart.find_one({"user_id": user_id, "product_id": product_id})

    if existing:
        db.cart.update_one(
            {"_id": existing["_id"]},
            {"$inc": {"quantity": quantity}},
        )
    else:
        db.cart.insert_one({
            "_id":        next_id(db, "cart"),
            "user_id":    user_id,
            "product_id": product_id,
            "quantity":   quantity,
        })


def update_cart_item(db, cart_id: int, user_id: int, quantity: int) -> None:
    """Update quantity. If quantity <= 0, remove the row."""
    if quantity <= 0:
        remove_cart_item(db, cart_id, user_id)
    else:
        db.cart.update_one(
            {"_id": cart_id, "user_id": user_id},
            {"$set": {"quantity": quantity}},
        )


def remove_cart_item(db, cart_id: int, user_id: int) -> None:
    """Delete one cart row (ownership-checked via user_id)."""
    db.cart.delete_one({"_id": cart_id, "user_id": user_id})


def clear_cart(db, user_id: int) -> None:
    """Empty the entire cart for a user (called after order placement)."""
    db.cart.delete_many({"user_id": user_id})
