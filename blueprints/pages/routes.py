"""
Future Store — Static / Support Pages Blueprint
Routes: /contact  /help  /returns  /privacy  /terms  /cookies

These are the footer "Support" and "Legal" destinations. Contact actually
persists submitted messages to MongoDB (a real, lightweight inbox) rather
than faking a success message with nowhere for the data to go; the rest
are informational pages with real, store-specific policy content.
"""
import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app_db import get_db, next_id
from services.cart_service import get_cart_count
from services.auth_service import current_user_id

pages_bp = Blueprint("pages", __name__)


def _cart_count_for_current_user(db) -> int:
    uid = current_user_id()
    return get_cart_count(db, uid) if uid else 0


# ─── contact ──────────────────────────────────────────────────────────────────

@pages_bp.route("/contact", methods=["GET", "POST"])
def contact():
    db = get_db()

    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        email   = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please fill in your name, email, and message.", "warning")
        else:
            db.contact_messages.insert_one({
                "_id":        next_id(db, "contact_messages"),
                "name":       name,
                "email":      email,
                "subject":    subject or "General inquiry",
                "message":    message,
                "created_at": datetime.datetime.utcnow(),
            })
            flash("Thanks for reaching out! Our team will get back to you within 24 hours.", "success")
            return redirect(url_for("pages.contact"))

    return render_template("pages/contact.html", cart_count=_cart_count_for_current_user(db))


# ─── help center ──────────────────────────────────────────────────────────────

@pages_bp.route("/help")
def help_center():
    db = get_db()
    return render_template("pages/help.html", cart_count=_cart_count_for_current_user(db))


# ─── returns ──────────────────────────────────────────────────────────────────

@pages_bp.route("/returns")
def returns():
    db = get_db()
    return render_template("pages/returns.html", cart_count=_cart_count_for_current_user(db))


# ─── legal ────────────────────────────────────────────────────────────────────

@pages_bp.route("/privacy")
def privacy():
    db = get_db()
    return render_template("pages/privacy.html", cart_count=_cart_count_for_current_user(db))


@pages_bp.route("/terms")
def terms():
    db = get_db()
    return render_template("pages/terms.html", cart_count=_cart_count_for_current_user(db))


@pages_bp.route("/cookies")
def cookies():
    db = get_db()
    return render_template("pages/cookies.html", cart_count=_cart_count_for_current_user(db))
