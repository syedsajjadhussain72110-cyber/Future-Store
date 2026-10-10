"""
Future Store — Customer Dashboard Blueprint
Routes: /dashboard

A single landing page for a logged-in customer: their profile info plus
a summary of their order history. Reuses the same service functions as
the orders blueprint rather than duplicating any database logic.
"""
from flask import Blueprint, render_template

from services.auth_service import login_required, current_user_id, get_user_by_id
from services.cart_service import get_cart_count
from services.order_service import get_orders_for_user, get_order_items_by_order
from app_db import get_db, with_id, with_ids

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def my_dashboard():
    db  = get_db()
    uid = current_user_id()

    user = with_id(get_user_by_id(uid, db))

    user_orders   = with_ids(get_orders_for_user(db, uid))
    order_ids     = [o["_id"] for o in user_orders]
    order_details = {oid: with_ids(items) for oid, items in get_order_items_by_order(db, order_ids).items()}

    # ── profile summary stats (computed from real order data, not fabricated) ─
    total_orders = len(user_orders)
    total_spent  = sum(o.get("total_price", 0) for o in user_orders)
    recent_orders = user_orders[:5]  # already sorted newest-first by the service

    cart_count = get_cart_count(db, uid)

    return render_template(
        "dashboard/dashboard.html",
        user=user,
        recent_orders=recent_orders,
        order_details=order_details,
        total_orders=total_orders,
        total_spent=total_spent,
        cart_count=cart_count,
    )
