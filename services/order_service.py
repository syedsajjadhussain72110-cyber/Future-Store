"""
Future Store — Order Service (MongoDB)
All order-related DB operations in one place.

This file is new: in the original SQLite version, order creation and the
admin order/dashboard queries were raw SQL written directly inside the
cart and admin blueprints. Centralising them here keeps the "blueprints
never write raw queries" rule consistent now that those queries are
Mongo aggregation pipelines instead of one-line SQL strings.
"""
import datetime
from app_db import next_id


# ─── checkout / order creation ────────────────────────────────────────────────

def create_order(db, user_id: int, items: list, tax_rate: float = 0.10) -> int:
    """
    Create an order + its order_items from a list of cart item dicts
    (as returned by cart_service.get_cart_items). Returns the new order id.
    """
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    total = round(subtotal * (1 + tax_rate), 2)

    order_id = next_id(db, "orders")
    db.orders.insert_one({
        "_id":         order_id,
        "user_id":     user_id,
        "total_price": total,
        "status":      "Confirmed",
        "created_at":  datetime.datetime.utcnow(),
    })

    order_items = []
    for item in items:
        order_items.append({
            "_id":        next_id(db, "order_items"),
            "order_id":   order_id,
            "product_id": item["id"],
            "quantity":   item["quantity"],
            "price":      item["price"],
        })
    if order_items:
        db.order_items.insert_many(order_items)

    return order_id


# ─── customer-facing ──────────────────────────────────────────────────────────

def get_orders_for_user(db, user_id: int) -> list:
    """Return this user's orders, newest first."""
    return list(db.orders.find({"user_id": user_id}).sort("created_at", -1))


def get_order_items_by_order(db, order_ids: list) -> dict:
    """
    Return {order_id: [item, ...]} for the given list of order ids, each
    item annotated with product name/image/brand (replaces the old
    JOIN order_items oi ON oi.product_id = p.id).
    """
    if not order_ids:
        return {}

    items = list(db.order_items.find({"order_id": {"$in": order_ids}}))
    product_ids = {i["product_id"] for i in items}
    products = db.products.find({"_id": {"$in": list(product_ids)}})
    product_by_id = {p["_id"]: p for p in products}

    details: dict = {oid: [] for oid in order_ids}
    for item in items:
        p = product_by_id.get(item["product_id"], {})
        item["name"]  = p.get("name", "Unknown product")
        item["image"] = p.get("image", "")
        item["brand"] = p.get("brand", "")
        details[item["order_id"]].append(item)
    return details


# ─── admin ────────────────────────────────────────────────────────────────────

def get_all_orders_admin(db) -> list:
    """
    Return every order, newest first, each annotated with the ordering
    user's name + email (replaces JOIN orders o JOIN users u).
    """
    orders = list(db.orders.find({}).sort("created_at", -1))
    if not orders:
        return orders

    user_ids = {o["user_id"] for o in orders}
    users = db.users.find({"_id": {"$in": list(user_ids)}})
    user_by_id = {u["_id"]: u for u in users}

    for o in orders:
        u = user_by_id.get(o["user_id"], {})
        o["user_name"] = u.get("name", "Unknown")
        o["email"]     = u.get("email", "")
    return orders


def update_order_status(db, order_id: int, status: str) -> None:
    db.orders.update_one({"_id": order_id}, {"$set": {"status": status}})


def get_order_count(db) -> int:
    return db.orders.count_documents({})


def get_total_revenue(db) -> float:
    pipeline = [
        {"$match": {"status": {"$ne": "Cancelled"}}},
        {"$group": {"_id": None, "s": {"$sum": "$total_price"}}},
    ]
    result = list(db.orders.aggregate(pipeline))
    return result[0]["s"] if result else 0


def get_recent_orders(db, limit: int = 10) -> list:
    """Recent orders annotated with user_name, for the admin dashboard."""
    orders = list(db.orders.find({}).sort("created_at", -1).limit(limit))
    if not orders:
        return orders
    user_ids = {o["user_id"] for o in orders}
    users = db.users.find({"_id": {"$in": list(user_ids)}})
    user_by_id = {u["_id"]: u for u in users}
    for o in orders:
        o["user_name"] = user_by_id.get(o["user_id"], {}).get("name", "Unknown")
    return orders


def get_top_products(db, limit: int = 5) -> list:
    """
    Best-selling products by number of order_item rows (replaces the old
    GROUP BY p.id ORDER BY order_count DESC).
    """
    pipeline = [
        {"$group": {"_id": "$product_id", "order_count": {"$sum": 1}}},
        {"$sort": {"order_count": -1}},
        {"$limit": limit},
    ]
    rows = list(db.order_items.aggregate(pipeline))
    product_ids = [r["_id"] for r in rows]
    products = db.products.find({"_id": {"$in": product_ids}})
    product_by_id = {p["_id"]: p for p in products}

    top = []
    for r in rows:
        p = product_by_id.get(r["_id"], {})
        top.append({
            "name":        p.get("name", "Unknown"),
            "brand":       p.get("brand", ""),
            "order_count": r["order_count"],
        })
    return top
