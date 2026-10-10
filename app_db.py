"""
Future Store — Database Connection Helper (MongoDB)
Provides a per-request MongoDB database handle.
Import get_db() wherever you need access to collections.

NOTE ON CONNECTIONS:
PyMongo's MongoClient already manages an internal connection pool, so
unlike sqlite3 it is NOT meant to be opened/closed per request. The
recommended pattern is one MongoClient per process (created once, lazily,
and cached), while still using Flask's `g` to hand out the *database*
handle per request for consistency with how the rest of the app expects
get_db() to behave. close_db() therefore does NOT close the underlying
TCP connection — it just clears the reference on `g`. The MongoClient
itself is closed only on app/process shutdown.
"""
import os
from flask import g, current_app
from pymongo import MongoClient, ASCENDING

# ─── module-level client (one per process, not per request) ──────────────────
_client: MongoClient | None = None


def _get_client() -> MongoClient:
    """Lazily create the single shared MongoClient for this process."""
    global _client
    if _client is None:
        uri = current_app.config.get("MONGO_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """
    Return a PyMongo Database handle stored on Flask's request context (g).
    The handle is cheap to create (no new socket per call) since it just
    references the shared MongoClient's connection pool.
    """
    if "db" not in g:
        client = _get_client()
        db_name = current_app.config.get("MONGO_DB", "future_store")
        g.db = client[db_name]
    return g.db


def close_db(error=None) -> None:
    """
    Request teardown hook (registered in create_app via teardown_appcontext).
    Mongo connections are pooled by the driver, so there is nothing to
    actually close per-request — we just drop the reference on g.
    """
    g.pop("db", None)


# ─── autoincrement-style integer IDs ───────────────────────────────────────────
# MongoDB's native _id is an ObjectId, but the rest of this app (routes,
# templates, <int:product_id> converters) expects plain incrementing
# integers like SQLite's AUTOINCREMENT. We emulate that with a small
# "counters" collection: one document per collection name, atomically
# incremented with $inc on every insert.

def next_id(db, collection_name: str) -> int:
    """
    Atomically return the next integer id for `collection_name`,
    creating the counter at 0 -> 1 if it doesn't exist yet.
    """
    result = db.counters.find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


def ensure_indexes(db) -> None:
    """
    Create the indexes/uniqueness constraints that SQLite previously gave
    us via PRIMARY KEY / UNIQUE / explicit CREATE INDEX statements.
    Safe to call repeatedly (create_index is idempotent).
    """
    db.users.create_index("email", unique=True)
    db.categories.create_index("name", unique=True)
    db.categories.create_index("slug", unique=True)

    db.products.create_index("category")
    db.products.create_index("category_id")
    db.products.create_index("slug")
    db.products.create_index("is_active")

    db.cart.create_index("user_id")
    db.cart.create_index([("user_id", ASCENDING), ("product_id", ASCENDING)])

    db.order_items.create_index("order_id")
    db.order_items.create_index("product_id")
    db.orders.create_index("user_id")

    db.reviews.create_index("product_id")
    db.reviews.create_index([("product_id", ASCENDING), ("user_id", ASCENDING)])

    db.contact_messages.create_index("created_at")


# ─── template-compatibility helper ─────────────────────────────────────────────
# All existing Jinja templates were written against sqlite3.Row objects,
# which exposed the primary key as row['id']. Mongo documents expose it as
# doc['_id']. Rather than rewrite every template right now (that's a
# separate, later task), every document handed to render_template() should
# be passed through with_id() so both product['_id'] and product['id'] work.

def with_id(doc):
    """Return doc with an 'id' key mirroring '_id' (no-op if doc is None)."""
    if doc is not None and "_id" in doc and "id" not in doc:
        doc["id"] = doc["_id"]
    return doc


def with_ids(docs):
    """Apply with_id() to a list of documents."""
    return [with_id(d) for d in docs]
