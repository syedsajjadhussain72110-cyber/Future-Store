"""
Future Store — Recommendation Service (MongoDB)
Powers the "AI Recommended Products" section on the product detail page.

Strategy (content-based, no separate model needed):
  1. Primary signal: other active products in the SAME category as the
     product being viewed, ranked by rating (best-rated first), tied
     evenly with the product's own price so suggestions stay in a
     comparable price band.
  2. Fallback: if the category doesn't have enough other products to fill
     the requested count (small categories, or a product whose category
     has no siblings), top up with globally trending (highest-rated)
     active products, still excluding the current product and anything
     already picked.

This keeps recommendations fast (two indexed Mongo queries, no joins
beyond what the rest of the app already does) and always returns
something relevant instead of an empty list, while never recommending
the product the customer is already looking at.
"""


def get_recommendations(db, product_id: int, n: int = 4) -> list:
    """
    Return up to `n` product ids recommended for someone viewing
    `product_id`. Always excludes `product_id` itself.
    """
    current = db.products.find_one({"_id": product_id})
    if not current:
        return []

    category = current.get("category", "")
    price = current.get("price", 0) or 0

    # ── 1. same-category candidates, closest price first, then rating ──────
    same_category = list(
        db.products.find({
            "is_active": 1,
            "category": category,
            "_id": {"$ne": product_id},
        })
    )

    def price_distance(p):
        return abs((p.get("price") or 0) - price)

    same_category.sort(key=lambda p: (price_distance(p), -(p.get("rating") or 0)))

    picked_ids = [p["_id"] for p in same_category[:n]]

    # ── 2. top up with trending products if the category was too small ────
    if len(picked_ids) < n:
        exclude_ids = set(picked_ids) | {product_id}
        topup = list(
            db.products.find({
                "is_active": 1,
                "_id": {"$nin": list(exclude_ids)},
            }).sort("rating", -1).limit(n - len(picked_ids))
        )
        picked_ids.extend(p["_id"] for p in topup)

    return picked_ids[:n]
