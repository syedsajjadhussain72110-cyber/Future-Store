"""
Future Store — One-time SQLite → MongoDB data migration.

Run this ONCE after setting up MongoDB, to carry over your existing
database.db data (products, users, cart, orders, reviews, etc.) into the
new Mongo collections, preserving the original integer ids so existing
URLs like /product/<id> keep working.

Usage:
    python migrate_sqlite_to_mongo.py

Safe to re-run: it wipes the target Mongo collections first, so re-running
won't create duplicates (but will overwrite Mongo with whatever is
currently in database.db).
"""
import sqlite3
import os
from pymongo import MongoClient

from config import Config
from app_db import ensure_indexes

SQLITE_PATH = os.environ.get("DATABASE", "database.db")

# Tables migrated as-is, one collection per table, integer ids preserved.
TABLES = [
    "categories", "products", "product_variants", "users",
    "cart", "orders", "order_items", "reviews",
    "inventory_log", "price_history",
]


def row_to_doc(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict with _id = old integer id."""
    doc = dict(row)
    if "id" in doc:
        doc["_id"] = doc.pop("id")
    return doc


def migrate():
    sconn = sqlite3.connect(SQLITE_PATH)
    sconn.row_factory = sqlite3.Row

    client = MongoClient(Config.MONGO_URI)
    db = client[Config.MONGO_DB]

    for table in TABLES:
        try:
            rows = sconn.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            print(f"  [skip] table '{table}' does not exist in {SQLITE_PATH}")
            continue

        docs = [row_to_doc(r) for r in rows]

        db[table].delete_many({})  # wipe target collection first
        if docs:
            db[table].insert_many(docs)
        print(f"  [ok] {table}: migrated {len(docs)} rows")

        # Seed the autoincrement counter so next_id() continues correctly
        if docs:
            max_id = max(d["_id"] for d in docs if isinstance(d["_id"], int))
            db.counters.update_one(
                {"_id": table},
                {"$set": {"seq": max_id}},
                upsert=True,
            )

    ensure_indexes(db)
    sconn.close()
    client.close()
    print("✅  Migration complete.")


if __name__ == "__main__":
    migrate()
