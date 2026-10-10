"""
Future Store — MongoDB Seed Script
Wipes products/categories/users and reloads them from products.json,
in the exact document shape the rest of the app (services/product_service.py,
app_db.py, blueprints/*) expects:

    products:   {_id: int, name, category, category_id, price, base_price,
                 rating, brand, description, image, stock, slug, sku,
                 is_active: 1}
    categories: {_id: int, name, slug, sort_order}
    users:      {_id: int, name, email, password (hashed), role}

IMPORTANT: is_active must be the int 1 (not Python True) and the primary
key must be _id (not "id") — every query in services/product_service.py
filters on {"is_active": 1} and looks products up by {"_id": product_id}.
"""
import json
import os
import re

from werkzeug.security import generate_password_hash

from app import create_app
from app_db import get_db, next_id, ensure_indexes
from services.image_utils import normalize_image

ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "")
ADMIN_NAME = "Store Admin"

# products.json may live at the project root or under static/ depending on
# where the script is run from — check both so this just works either way.
PRODUCTS_JSON_CANDIDATES = ["products.json", os.path.join("static", "products.json")]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


def load_products() -> list:
    for path in PRODUCTS_JSON_CANDIDATES:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(
        f"products.json not found in any of: {PRODUCTS_JSON_CANDIDATES}"
    )


def seed_categories(db, products: list) -> dict:
    """Insert one doc per distinct category, return {name: category_id}."""
    names = sorted({p["category"] for p in products})
    category_map = {}

    for index, name in enumerate(names):
        slug = slugify(name)
        cat_id = next_id(db, "categories")
        db.categories.insert_one({
            "_id": cat_id,
            "name": name,
            "slug": slug,
            "sort_order": index,
        })
        category_map[name] = cat_id

    return category_map


def seed_admin(db) -> None:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("Administrator skipped: register an account or set SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD locally.")
        return
    if len(ADMIN_PASSWORD) < 12:
        raise ValueError("Use a SEED_ADMIN_PASSWORD of at least 12 characters.")
    password_hash = generate_password_hash(ADMIN_PASSWORD)
    existing = db.users.find_one({"email": ADMIN_EMAIL})

    if existing:
        db.users.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"name": ADMIN_NAME, "password": password_hash, "role": "admin"}},
        )
    else:
        db.users.insert_one({
            "_id": next_id(db, "users"),
            "name": ADMIN_NAME,
            "email": ADMIN_EMAIL,
            "password": password_hash,
            "role": "admin",
        })


def seed():
    app = create_app()
    with app.app_context():
        db = get_db()

        products = load_products()
        if any(db[name].count_documents({}) for name in ("products", "categories", "users", "cart", "orders", "reviews")):
            raise RuntimeError("Seed only an empty demo database. Choose a new MONGO_DB to preserve existing data.")

        # Wipe collections we're about to reseed. (Cart/orders/reviews are
        # left alone — they reference product ids that are about to be
        # reassigned anyway if you re-run this, so only do that if you also
        # intend to reset those.)
        db.products.delete_many({})
        db.categories.delete_many({})
        db.users.delete_many({})

        category_map = seed_categories(db, products)

        for index, product in enumerate(products):
            category_name = product["category"]
            price = float(product["price"])
            new_id = next_id(db, "products")

            db.products.insert_one({
                "_id":         new_id,
                "name":        product["name"],
                "category":    category_name,
                "category_id": category_map[category_name],
                "price":       price,
                "base_price":  price,
                "rating":      float(product.get("rating", 4.0)),
                "brand":       product.get("brand", ""),
                "description": product.get("description", ""),
                "image":       normalize_image(product.get("image", "")),
                "stock":       int(product.get("stock", 50)),
                "slug":        slugify(product["name"]),
                "sku":         f"FS-{index + 1:04d}",
                "is_active":   1,
            })

        print(f"✅ Seeded {len(products)} products across {len(category_map)} categories.")

        seed_admin(db)
        print("Administrator setup completed; credentials are never printed.")

        ensure_indexes(db)
        print("✅ Indexes ensured.")
        print("🚀 Database seeding completed successfully!")


if __name__ == "__main__":
    seed()
