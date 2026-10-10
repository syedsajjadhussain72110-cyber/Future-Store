"""
Future Store — Auth Service (MongoDB)
Handles password hashing, verification, and session helpers.
Uses werkzeug (same library Flask uses internally) — consistent across
seed_db.py and the live app.
"""
from functools import wraps

from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

from app_db import next_id


# ─── password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a Werkzeug-hashed password string."""
    return generate_password_hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored hash."""
    return check_password_hash(hashed, plain)


# ─── user lookup ──────────────────────────────────────────────────────────────

def get_user_by_email(email: str, db):
    """Fetch a user document by email (case-insensitive). Returns dict or None.

    Mongo has no built-in LOWER(); we match case-insensitively with a
    regex anchored to the whole string instead, escaping the input so a
    user's email can't be used to inject a regex pattern.
    """
    import re
    pattern = f"^{re.escape(email)}$"
    return db.users.find_one({"email": {"$regex": pattern, "$options": "i"}})


def get_user_by_id(user_id: int, db):
    """Fetch a user document by integer id. Returns dict or None."""
    return db.users.find_one({"_id": user_id})


def create_user(db, name: str, email: str, password: str, role: str = "customer") -> dict:
    """Insert a new user document and return it."""
    user = {
        "_id":      next_id(db, "users"),
        "name":     name,
        "email":    email,
        "password": hash_password(password),
        "role":     role,
    }
    db.users.insert_one(user)
    return user


# ─── session helpers ──────────────────────────────────────────────────────────

def login_user(user) -> None:
    """Populate Flask session from a user document (dict-like, _id as pk)."""
    session["user_id"]   = user["_id"]
    session["user_name"] = user["name"]
    session["user_role"] = user["role"]


def logout_user() -> None:
    """Clear Flask session."""
    session.clear()


def current_user_id() -> int | None:
    return session.get("user_id")


def is_logged_in() -> bool:
    return "user_id" in session


def is_admin() -> bool:
    return session.get("user_role") == "admin"


# ─── decorators ───────────────────────────────────────────────────────────────

def login_required(f):
    """Redirect to /auth/login when user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Redirect to home when user is not an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash("Please sign in.", "warning")
            return redirect(url_for("auth.login"))
        if not is_admin():
            flash("Admin access required.", "danger")
            return redirect(url_for("store.index"))
        return f(*args, **kwargs)
    return decorated
