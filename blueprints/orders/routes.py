"""
Future Store — Orders Blueprint
Routes: /orders
"""
from flask import Blueprint, render_template

from services.auth_service import login_required, current_user_id
from services.cart_service import get_cart_count
from services.order_service import get_orders_for_user, get_order_items_by_order
from app_db import get_db, with_ids

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


@orders_bp.route("/")
@login_required
def my_orders():
    db  = get_db()
    uid = current_user_id()

    user_orders = with_ids(get_orders_for_user(db, uid))
    order_ids   = [o["_id"] for o in user_orders]
    order_details = {oid: with_ids(items) for oid, items in get_order_items_by_order(db, order_ids).items()}

    cart_count = get_cart_count(db, uid)

    return render_template(
        "orders/orders.html",
        orders=user_orders,
        order_details=order_details,
        cart_count=cart_count,
    )