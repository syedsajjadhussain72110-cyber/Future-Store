"""
Future Store — Application Factory
Usage:
    python app.py          (dev server)
    flask run              (flask CLI)
"""
import os
import datetime
from flask import Flask, session

from config import config_map
from app_db import close_db, get_db, ensure_indexes
from services.image_utils import normalize_image


def format_date(value, fmt: str = "%b %d, %Y") -> str:
    """
    Jinja filter: render a created_at value as a clean date string.

    MongoDB stores created_at as a real datetime object (the old SQLite
    version stored it as a string and templates used to slice the first
    10 characters, e.g. created_at[:10], to get YYYY-MM-DD — that breaks
    now since datetimes aren't subscriptable). This filter accepts either
    a datetime or a legacy ISO-style string so it works regardless.
    """
    if value is None:
        return ""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.strftime(fmt)
    # fall back for any leftover plain strings (e.g. un-migrated data)
    return str(value)[:10]


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_map.get(env, config_map["default"]))
    if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "replace-with-a-random-local-secret":
        raise RuntimeError("Set SECRET_KEY in your local .env before starting Future Store.")
    app.jinja_env.filters["format_date"] = format_date
    app.jinja_env.globals["product_image"] = normalize_image

    # ── teardown ──────────────────────────────────────────────────────────────
    app.teardown_appcontext(close_db)

    # ── one-time index setup ────────────────────────────────────────────────
    # Mongo has no schema migration step like init_db.py used to run, but
    # indexes (including unique constraints that replace SQLite's UNIQUE)
    # still need to be created explicitly. create_index() is idempotent,
    # so this is safe to run on every app start.
    with app.app_context():
        ensure_indexes(get_db())

    # ── blueprints ────────────────────────────────────────────────────────────
    from blueprints.auth.routes      import auth_bp
    from blueprints.store.routes     import store_bp
    from blueprints.cart.routes      import cart_bp
    from blueprints.orders.routes    import orders_bp
    from blueprints.admin.routes     import admin_bp
    from blueprints.dashboard.routes import dashboard_bp
    from blueprints.pages.routes     import pages_bp
    from blueprints.ai.routes        import ai_bp

    app.register_blueprint(auth_bp)       # /auth/login  /auth/register  /auth/logout
    app.register_blueprint(store_bp)      # /  /product/<id>
    app.register_blueprint(cart_bp)       # /cart  /cart/add  /cart/checkout
    app.register_blueprint(orders_bp)     # /orders
    app.register_blueprint(admin_bp)      # /admin
    app.register_blueprint(dashboard_bp)  # /dashboard
    app.register_blueprint(pages_bp)      # /contact  /help  /returns  /privacy  /terms  /cookies
    app.register_blueprint(ai_bp)         # /ai/chat

    # ── global template context ───────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from services.product_service import get_all_categories
        return dict(
            current_user    = session.get("user_name"),
            current_role    = session.get("user_role"),
            user_logged_in  = "user_id" in session,
            nav_categories  = get_all_categories(get_db()),
        )

    return app


# ─── dev entry point ──────────────────────────────────────────────────────────
app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
