"""
カテゴリ管理API（ユーザーごとにスコープ）
  GET    /api/categories
  POST   /api/categories
  PUT    /api/categories/{id}
  DELETE /api/categories/{id}
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import uuid

from models import Category
import db

categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")


@categories_bp.get("")
@login_required
def list_categories():
    return jsonify([c.to_dict() for c in db.get_all_categories(current_user.id)])


@categories_bp.post("")
@login_required
def create_category():
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "カテゴリ名は必須です"}), 400

    existing = db.get_all_categories(current_user.id)
    if any(c.name == name for c in existing):
        return jsonify({"detail": "同じ名前のカテゴリが既にあります"}), 409

    next_order = (max((c.sort_order for c in existing), default=0)) + 1
    cat = Category(
        id="cat-" + uuid.uuid4().hex[:12],
        name=name,
        emoji=(body.get("emoji") or "📦").strip(),
        color=(body.get("color") or "#9ca3af").strip(),
        sort_order=next_order,
    )
    return jsonify(db.add_category(current_user.id, cat).to_dict()), 201


@categories_bp.put("/<cat_id>")
@login_required
def edit_category(cat_id: str):
    body = request.get_json() or {}
    fields = {}
    if "name" in body:
        name = (body["name"] or "").strip()
        if not name:
            return jsonify({"detail": "カテゴリ名は空にできません"}), 400
        if any(c.name == name and c.id != cat_id for c in db.get_all_categories(current_user.id)):
            return jsonify({"detail": "同じ名前のカテゴリが既にあります"}), 409
        fields["name"] = name
    if "emoji" in body:
        fields["emoji"] = (body["emoji"] or "📦").strip()
    if "color" in body:
        fields["color"] = (body["color"] or "#9ca3af").strip()
    if "sort_order" in body:
        try:
            fields["sort_order"] = int(body["sort_order"])
        except (TypeError, ValueError):
            pass
    if not fields:
        return jsonify({"detail": "更新項目がありません"}), 400
    if not db.update_category(current_user.id, cat_id, fields):
        return jsonify({"detail": "カテゴリが見つかりません"}), 404
    return jsonify({"ok": True, **fields})


@categories_bp.delete("/<cat_id>")
@login_required
def remove_category(cat_id: str):
    if not db.delete_category(current_user.id, cat_id):
        return jsonify({"detail": "カテゴリが見つかりません"}), 404
    return "", 204
