"""
Future Store — Admin Blueprint
Routes: /admin  /admin/products  /admin/products/add  /admin/products/delete/<id>
        /admin/orders  /admin/orders/update/<id>
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from services.auth_service import admin_required, current_user_id
from services.product_service import (
    get_all_products_admin, create_product, delete_product,
)
from services.cart_service import get_cart_count
from services.order_service import (
    get_order_count, get_total_revenue, get_recent_orders, get_top_products,
    get_all_orders_admin, update_order_status,
)
from app_db import get_db, with_id, with_ids

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ─── dashboard ────────────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    db = get_db()

    total_products = db.products.count_documents({"is_active": 1})
    total_users    = db.users.count_documents({})
    total_orders   = get_order_count(db)
    total_revenue  = get_total_revenue(db)

    recent_orders  = with_ids(get_recent_orders(db, limit=10))
    top_products   = get_top_products(db, limit=5)

    low_stock = with_ids(list(
        db.products.find({"stock": {"$lte": 10}, "is_active": 1}).sort("stock", 1).limit(10)
    ))

    cart_count = get_cart_count(db, current_user_id())

    return render_template(
        "admin/dashboard.html",
        total_products=total_products,
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_orders=recent_orders,
        top_products=top_products,
        low_stock=low_stock,
        cart_count=cart_count,
    )


# ─── products ─────────────────────────────────────────────────────────────────

@admin_bp.route("/products")
@admin_required
def products():
    db       = get_db()
    products = with_ids(get_all_products_admin(db))
    count    = get_cart_count(db, current_user_id())
    return render_template("admin/products.html", products=products, cart_count=count)


@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    db = get_db()
    if request.method == "POST":
        create_product(db, request.form)
        flash("Product added successfully! ✅", "success")
        return redirect(url_for("admin.products"))

    count = get_cart_count(db, current_user_id())
    return render_template("admin/add_product.html", cart_count=count)


@admin_bp.route("/products/delete/<int:product_id>")
@admin_required
def remove_product(product_id: int):
    db = get_db()
    delete_product(db, product_id)
    flash("Product removed.", "info")
    return redirect(url_for("admin.products"))


# ─── orders ───────────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
@admin_required
def orders():
    db = get_db()
    all_orders = with_ids(get_all_orders_admin(db))
    count = get_cart_count(db, current_user_id())
    return render_template("admin/orders.html", orders=all_orders, cart_count=count)


@admin_bp.route("/orders/update/<int:order_id>", methods=["POST"])
@admin_required
def update_order(order_id: int):
    status = request.form.get("status", "Pending")
    db     = get_db()
    update_order_status(db, order_id, status)
    flash(f"Order #{order_id} updated to '{status}'.", "success")
    return redirect(url_for("admin.orders"))