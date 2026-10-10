"""
Future Store — Store Blueprint
Routes: /  /product/<id>  /search  /review/<id>
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.product_service import (
    get_products, get_product_by_id, get_all_categories,
    get_trending, get_new_arrivals, get_products_by_category_groups,
    get_reviews, get_avg_rating, add_review,
)
from services.cart_service import get_cart_count
from services.auth_service import login_required, current_user_id
from app_db import get_db, with_id, with_ids

store_bp = Blueprint("store", __name__)


# ─── home / search ────────────────────────────────────────────────────────────

@store_bp.route("/")
def index():
    db = get_db()

    # ── filter params (unified under "search" — fixes old q/search mismatch) ─
    search     = request.args.get("search", "").strip()
    category   = request.args.get("category", "")
    min_price  = request.args.get("min_price", "")
    max_price  = request.args.get("max_price", "")
    min_rating = request.args.get("min_rating", "")
    sort       = request.args.get("sort", "")

    products   = with_ids(get_products(db, search, category, min_price, max_price, min_rating, sort))
    categories = get_all_categories(db)
    trending   = with_ids(get_trending(db, limit=8))
    new_arrivals = with_ids(get_new_arrivals(db, limit=8))

    # carousel: top categories, a handful of products each
    carousel_categories = categories[:6]
    carousel_groups = {
        cat: with_ids(items)
        for cat, items in get_products_by_category_groups(db, carousel_categories, per_category=8).items()
    }

    cart_count = get_cart_count(db, current_user_id()) if current_user_id() else 0

    return render_template(
        "store/index.html",
        products=products,
        categories=categories,
        trending=trending,
        new_arrivals=new_arrivals,
        carousel_categories=carousel_categories,
        carousel_groups=carousel_groups,
        search=search,
        selected_category=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        sort=sort,
        cart_count=cart_count,
    )


# ─── product detail ───────────────────────────────────────────────────────────

@store_bp.route("/product/<int:product_id>")
def product_detail(product_id: int):
    db         = get_db()
    product    = with_id(get_product_by_id(db, product_id))

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("store.index"))

    reviews    = with_ids(get_reviews(db, product_id))
    avg_rating = get_avg_rating(db, product_id)

    # ── recommendations (imported lazily to avoid circular import) ──────────
    try:
        from services.recommendation_service import get_recommendations
        rec_ids = get_recommendations(db, product_id, n=4)
    except Exception:
        rec_ids = []

    recommendations = []
    for rid in rec_ids:
        rec = get_product_by_id(db, rid)
        if rec:
            recommendations.append(with_id(rec))

    cart_count = get_cart_count(db, current_user_id()) if current_user_id() else 0

    return render_template(
        "store/product.html",
        product=product,
        recommendations=recommendations,
        reviews=reviews,
        avg_rating=avg_rating,
        cart_count=cart_count,
    )


# ─── submit review ────────────────────────────────────────────────────────────

@store_bp.route("/review/<int:product_id>", methods=["POST"])
@login_required
def submit_review(product_id: int):
    rating  = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "").strip()

    db = get_db()
    ok = add_review(db, product_id, current_user_id(), rating, comment)

    if ok:
        flash("Your review has been submitted. Thank you!", "success")
    else:
        flash("You have already reviewed this product.", "warning")

    return redirect(url_for("store.product_detail", product_id=product_id))