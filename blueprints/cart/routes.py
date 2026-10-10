"""
Future Store — Cart Blueprint
Routes: /cart  /cart/add/<id>  /cart/update/<id>  /cart/remove/<id>  /checkout
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from services.cart_service import (
    get_cart_items, get_cart_count, get_cart_total,
    add_to_cart, update_cart_item, remove_cart_item, clear_cart,
)
from services.order_service import create_order
from services.auth_service import login_required, current_user_id
from app_db import get_db

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


# ─── view cart ────────────────────────────────────────────────────────────────

@cart_bp.route("/")
@login_required
def view_cart():
    db    = get_db()
    uid   = current_user_id()
    items = get_cart_items(db, uid)
    total = get_cart_total(items)
    count = get_cart_count(db, uid)
    return render_template("cart/cart.html", items=items, total=total, cart_count=count)


# ─── add ──────────────────────────────────────────────────────────────────────

@cart_bp.route("/add/<int:product_id>", methods=["POST"])
@login_required
def add(product_id: int):
    try:
        qty = max(1, int(request.form.get("quantity", 1)))
    except ValueError:
        qty = 1

    db = get_db()
    add_to_cart(db, current_user_id(), product_id, qty)

    flash("Item added to cart! 🛒", "success")
    # redirect back to wherever the user was
    return redirect(request.referrer or url_for("store.index"))


# ─── update ───────────────────────────────────────────────────────────────────

@cart_bp.route("/update/<int:cart_id>", methods=["POST"])
@login_required
def update(cart_id: int):
    try:
        qty = int(request.form.get("quantity", 1))
    except ValueError:
        qty = 1

    db = get_db()
    update_cart_item(db, cart_id, current_user_id(), qty)
    return redirect(url_for("cart.view_cart"))


# ─── remove ───────────────────────────────────────────────────────────────────

@cart_bp.route("/remove/<int:cart_id>")
@login_required
def remove(cart_id: int):
    db = get_db()
    remove_cart_item(db, cart_id, current_user_id())
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart.view_cart"))


# ─── checkout ─────────────────────────────────────────────────────────────────

@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    db    = get_db()
    uid   = current_user_id()
    items = get_cart_items(db, uid)

    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart.view_cart"))

    total = get_cart_total(items)
    count = get_cart_count(db, uid)

    if request.method == "POST":
        order_id = create_order(db, uid, items, tax_rate=0.10)  # 10% tax included
        clear_cart(db, uid)

        flash(f"Order #{order_id} placed successfully! 🎉", "success")
        return redirect(url_for("orders.my_orders"))

    return render_template("cart/checkout.html", items=items, total=total, cart_count=count)