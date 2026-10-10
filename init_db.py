"""
Future Store — Database Initialiser
Run once: python init_db.py
Safe to re-run (uses IF NOT EXISTS + ALTER-IF-MISSING).
"""
import sqlite3
import os

DB_PATH = os.environ.get("DATABASE", "database.db")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _col_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _add_col(cursor, table: str, column: str, definition: str):
    """Add a column only if it is missing (safe migration helper)."""
    if not _col_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  [migrate] Added {table}.{column}")


# ─── schema ───────────────────────────────────────────────────────────────────

def init_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # ── categories ────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            slug       TEXT    NOT NULL UNIQUE,
            parent_id  INTEGER,
            image      TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES categories(id)
        )
    """)

    # ── products ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            category_id INTEGER,
            price       REAL    NOT NULL,
            base_price  REAL,
            rating      REAL    DEFAULT 0,
            brand       TEXT,
            description TEXT,
            image       TEXT,
            stock       INTEGER DEFAULT 0,
            slug        TEXT,
            sku         TEXT,
            is_active   INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # ── product variants ──────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS product_variants (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL,
            variant_name TEXT    NOT NULL,
            sku          TEXT,
            price_delta  REAL    DEFAULT 0,
            stock        INTEGER DEFAULT 0,
            attributes   TEXT,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ── users ─────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            role       TEXT    DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ── cart ──────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            variant_id INTEGER,
            quantity   INTEGER DEFAULT 1,
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (variant_id) REFERENCES product_variants(id)
        )
    """)

    # ── orders ────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            total_price REAL    NOT NULL,
            status      TEXT    DEFAULT 'Pending',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ── order items ───────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            variant_id INTEGER,
            quantity   INTEGER NOT NULL,
            price      REAL    NOT NULL,
            FOREIGN KEY (order_id)   REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (variant_id) REFERENCES product_variants(id)
        )
    """)

    # ── reviews ───────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id        INTEGER NOT NULL,
            user_id           INTEGER NOT NULL,
            rating            INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment           TEXT,
            verified_purchase INTEGER DEFAULT 0,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (user_id)    REFERENCES users(id)
        )
    """)

    # ── inventory log ─────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variant_id INTEGER,
            change_qty INTEGER NOT NULL,
            reason     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (variant_id) REFERENCES product_variants(id)
        )
    """)

    # ── price history ─────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price  REAL,
            new_price  REAL    NOT NULL,
            reason     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ── safe migrations (add columns that may be missing in older DBs) ────────
    _add_col(c, "products",    "base_price", "REAL")
    _add_col(c, "products",    "slug",       "TEXT")
    _add_col(c, "products",    "sku",        "TEXT")
    _add_col(c, "products",    "is_active",  "INTEGER DEFAULT 1")
    _add_col(c, "products",    "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    _add_col(c, "products",    "category_id","INTEGER")
    _add_col(c, "cart",        "variant_id", "INTEGER")
    _add_col(c, "order_items", "variant_id", "INTEGER")
    _add_col(c, "reviews",     "verified_purchase", "INTEGER DEFAULT 0")

    # ── indexes ───────────────────────────────────────────────────────────────
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_slug        ON products(slug)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order    ON order_items(order_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product  ON order_items(product_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product      ON reviews(product_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cart_user            ON cart(user_id)")

    conn.commit()
    conn.close()
    print(f"✅  Database ready at '{db_path}'")


if __name__ == "__main__":
    init_db()