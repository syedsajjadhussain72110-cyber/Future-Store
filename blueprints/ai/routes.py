"""
Future Store — AI Assistant Blueprint
Routes: /ai/chat

A small JSON API the floating chat widget calls. Keeps a short rolling
history in the Flask session (per browser) purely so the widget can
re-render past turns on page navigation; the actual answer logic in
services/ai_service.py is stateless per call.
"""
from flask import Blueprint, request, jsonify, session

from app_db import get_db
from services.ai_service import answer

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")

MAX_HISTORY = 20  # messages kept in session, oldest dropped first


@ai_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Message is required."}), 400

    if len(user_message) > 500:
        user_message = user_message[:500]

    db = get_db()
    history = session.get("ai_chat_history", [])

    result = answer(db, user_message, history)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": result["reply"]})
    session["ai_chat_history"] = history[-MAX_HISTORY:]

    return jsonify(result)


@ai_bp.route("/chat/reset", methods=["POST"])
def reset_chat():
    session.pop("ai_chat_history", None)
    return jsonify({"ok": True})
