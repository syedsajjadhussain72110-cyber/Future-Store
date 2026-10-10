"""
Future Store — Auth Blueprint
Routes: /auth/login  /auth/register  /auth/logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from services.auth_service import (
    hash_password, verify_password,
    get_user_by_email, create_user, login_user, logout_user, is_logged_in,
)
from app_db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─── register ────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if is_logged_in():
        return redirect(url_for("store.index"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── validation ───────────────────────────────────────────────────────
        errors = []
        if not name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html")

        db = get_db()
        if get_user_by_email(email, db):
            flash("An account with that email already exists.", "warning")
            return render_template("auth/register.html")

        user = create_user(db, name, email, password)

        login_user(user)
        flash(f"Welcome, {name}! Your account has been created. 🎉", "success")
        return redirect(url_for("store.index"))

    return render_template("auth/register.html")


# ─── login ────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("store.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db   = get_db()
        user = get_user_by_email(email, db)

        if user and verify_password(password, user["password"]):
            login_user(user)
            flash(f"Welcome back, {user['name']}! 👋", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("store.index"))

        flash("Incorrect email or password.", "danger")

    return render_template("auth/login.html")


# ─── logout ───────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("store.index"))