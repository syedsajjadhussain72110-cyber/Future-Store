"""
Future Store — Product Service (MongoDB)
All product-related DB queries live here.
Blueprints call these functions; they never write raw queries themselves.
"""
from app_db import next_id
from services.image_utils import normalize_image


# ─── search / listing ─────────────────────────────────────────────────────────

def get_products(db,
                 search: str = "",
                 category: str = "",
                 min_price: str = "",
                 max_price: str = "",
                 min_rating: str = "",
                 sort: str = "") -> list:
    """
    Return filtered + sorted product documents.
    All parameters are optional strings (from request.args), mirroring the
    original SQL version's behaviour (silently ignored if not parseable).
    """
    query: dict = {"is_active": 1}

    if search:
        # Case-insensitive substring match across several fields, equivalent
        # to the old "LIKE '%term%'" OR-chain.
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex},
            {"description": regex},
            {"brand": regex},
            {"category": regex},
        ]

    if category:
        query["category"] = category

    price_filter = {}
    if min_price:
        try:
            price_filter["$gte"] = float(min_price)
        except ValueError:
            pass
    if max_price:
        try:
            price_filter["$lte"] = float(max_price)
        except ValueError:
            pass
    if price_filter:
        query["price"] = price_filter

    if min_rating:
        try:
            query["rating"] = {"$gte": float(min_rating)}
        except ValueError:
            pass

    sort_map = {
        "price_asc":  [("price", 1)],
        "price_desc": [("price", -1)],
        "rating":     [("rating", -1)],
        "newest":     [("_id", -1)],
    }
    sort_spec = sort_map.get(sort, [("_id", 1)])

    return list(db.products.find(query).sort(sort_spec))


def get_product_by_id(db, product_id: int):
    """Return a single product document or None."""
    return db.products.find_one({"_id": product_id, "is_active": 1})


def get_all_categories(db) -> list[str]:
    """Return a sorted list of distinct category name strings."""
    categories = db.products.distinct("category", {"is_active": 1})
    return sorted(categories)


def get_trending(db, limit: int = 8) -> list:
    """Return top-rated active products."""
    return list(
        db.products.find({"is_active": 1}).sort("rating", -1).limit(limit)
    )


def get_new_arrivals(db, limit: int = 8) -> list:
    """Return newest active products."""
    return list(
        db.products.find({"is_active": 1}).sort("_id", -1).limit(limit)
    )


def get_products_by_category_groups(db, categories: list, per_category: int = 8) -> dict:
    """
    Return {category_name: [products...]} for each given category, sorted
    by rating (best-rated first within the category). Used to power the
    homepage's category-tabbed product carousel.
    """
    groups = {}
    for cat in categories:
        groups[cat] = list(
            db.products.find({"is_active": 1, "category": cat})
                       .sort("rating", -1)
                       .limit(per_category)
        )
    return groups


# ─── admin helpers ────────────────────────────────────────────────────────────

def get_all_products_admin(db) -> list:
    """Return all products (including inactive) for admin panel."""
    return list(db.products.find({}).sort([("category", 1), ("name", 1)]))


def create_product(db, data: dict) -> int:
    """Insert a new product; return the new product id."""
    new_id = next_id(db, "products")
    price = float(data["price"])
    db.products.insert_one({
        "_id":         new_id,
        "name":        data["name"],
        "category":    data["category"],
        "price":       price,
        "base_price":  price,
        "rating":      float(data.get("rating", 4.0)),
        "brand":       data.get("brand", ""),
        "description": data.get("description", ""),
        "image":       normalize_image(data.get("image", ""), placeholder=""),
        "stock":       int(data.get("stock", 50)),
        "is_active":   1,
    })
    return new_id


def delete_product(db, product_id: int) -> None:
    """Soft-delete: set is_active = 0."""
    db.products.update_one({"_id": product_id}, {"$set": {"is_active": 0}})


# ─── reviews ──────────────────────────────────────────────────────────────────

def get_reviews(db, product_id: int) -> list:
    """
    Return reviews for a product, newest first, each annotated with the
    reviewing user's name (replaces the old JOIN users ON r.user_id = u.id).
    """
    reviews = list(
        db.reviews.find({"product_id": product_id}).sort("created_at", -1)
    )
    if not reviews:
        return reviews

    user_ids = {r["user_id"] for r in reviews}
    users = db.users.find({"_id": {"$in": list(user_ids)}})
    name_by_id = {u["_id"]: u["name"] for u in users}

    for r in reviews:
        r["user_name"] = name_by_id.get(r["user_id"], "Unknown")
    return reviews


def get_avg_rating(db, product_id: int) -> float | None:
    pipeline = [
        {"$match": {"product_id": product_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]
    result = list(db.reviews.aggregate(pipeline))
    return result[0]["avg"] if result else None


def add_review(db, product_id: int,
               user_id: int, rating: int, comment: str) -> bool:
    """Return False if the user already reviewed this product."""
    existing = db.reviews.find_one({"product_id": product_id, "user_id": user_id})
    if existing:
        return False

    import datetime
    db.reviews.insert_one({
        "_id":        next_id(db, "reviews"),
        "product_id": product_id,
        "user_id":    user_id,
        "rating":     rating,
        "comment":    comment,
        "created_at": datetime.datetime.utcnow(),
    })
    return True
