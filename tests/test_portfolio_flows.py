import pytest


@pytest.mark.parametrize("path", ["/", "/product/1", "/auth/login", "/auth/register", "/help", "/returns", "/privacy", "/terms", "/cookies", "/contact"])
def test_public_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_search_filters(client):
    response = client.get("/?search=Speaker&category=Electronics&max_price=100")
    assert response.status_code == 200
    assert b"Demo Speaker" in response.data


def test_registration_hashes_password_and_login(registered_client, db):
    user = db.users.find_one({"email": "user@example.test"})
    assert user["password"] != "sample-test-password"
    registered_client.get("/auth/logout")
    assert registered_client.post("/auth/login", data={"email": "user@example.test", "password": "wrong"}).status_code == 200
    assert registered_client.post("/auth/login", data={"email": "user@example.test", "password": "sample-test-password"}).status_code == 302


def test_cart_checkout_and_order_history(registered_client, db):
    client = registered_client
    assert client.post("/cart/add/1", data={"quantity": 2}).status_code == 302
    assert b"Demo Headphones" in client.get("/cart/").data
    assert client.get("/cart/checkout").status_code == 200
    assert client.post("/cart/checkout").status_code == 302
    order = db.orders.find_one({})
    assert order["total_price"] == 176.0
    assert db.order_items.count_documents({"order_id": order["_id"]}) == 1
    assert db.cart.count_documents({}) == 0
    assert b"Demo Headphones" in client.get("/orders/").data
    assert client.get("/dashboard/").status_code == 200


def test_review_and_duplicate_rejection(registered_client, db):
    data = {"rating": 5, "comment": "Useful demo product"}
    assert registered_client.post("/review/1", data=data).status_code == 302
    registered_client.post("/review/1", data=data)
    assert db.reviews.count_documents({"product_id": 1}) == 1
    assert b"Useful demo product" in registered_client.get("/product/1").data


def test_admin_access_and_store_management(registered_client, db):
    client = registered_client
    assert client.get("/admin/").status_code == 302
    with client.session_transaction() as session:
        session["user_role"] = "admin"
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/products").status_code == 200
    assert client.get("/admin/orders").status_code == 200
    assert client.post("/admin/products/add", data={"name": "New Demo Product", "category": "Books", "price": "20"}).status_code == 302
    product = db.products.find_one({"name": "New Demo Product"})
    client.get(f"/admin/products/delete/{product['_id']}")
    assert db.products.find_one({"_id": product["_id"]})["is_active"] == 0


def test_recommendations_exclude_current_and_inactive(db):
    from services.recommendation_service import get_recommendations
    assert get_recommendations(db, 1, 3) == [2, 3]
    assert get_recommendations(db, 999) == []


def test_assistant_catalog_and_demo_payment_policy(client):
    response = client.post("/ai/chat", json={"message": "show headphones under $100"})
    assert response.status_code == 200
    assert [p["id"] for p in response.json["products"]] == [2, 1]
    assert "no card or wallet payment is processed" in client.post("/ai/chat", json={"message": "payment methods?"}).json["reply"]
    assert client.post("/ai/chat", json={"message": ""}).status_code == 400
    assert client.post("/ai/chat/reset").json == {"ok": True}


def test_seed_refuses_existing_data(application, db):
    import seed_db
    with pytest.raises(RuntimeError, match="empty demo database"):
        seed_db.seed()
    assert db.products.count_documents({}) == 4


def test_seed_creates_catalog_without_default_admin(application, monkeypatch):
    import seed_db
    from app_db import get_db
    monkeypatch.setattr(seed_db, "ADMIN_EMAIL", "")
    monkeypatch.setattr(seed_db, "ADMIN_PASSWORD", "")
    seed_db.seed()
    with application.app_context():
        database = get_db()
        assert database.products.count_documents({}) == 91
        assert database.categories.count_documents({}) > 1
        assert database.users.count_documents({}) == 0


def test_application_rejects_missing_session_key(application, monkeypatch):
    from config import DevelopmentConfig
    from app import create_app
    monkeypatch.setattr(DevelopmentConfig, "SECRET_KEY", None)
    with pytest.raises(RuntimeError, match="Set SECRET_KEY"):
        create_app()
