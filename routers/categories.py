"""
カテゴリ管理APIルーター
  GET    /api/categories        - 一覧
  POST   /api/categories        - 追加
  PUT    /api/categories/{id}    - 名称・絵文字・色の変更
  DELETE /api/categories/{id}    - 削除
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
import uuid

from models import Category
import db

categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")


@categories_bp.get("")
@login_required
def list_categories():
    cats = db.get_all_categories()
    return jsonify([c.to_dict() for c in cats])


@categories_bp.post("")
@login_required
def create_category():
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"detail": "カテゴリ名は必須です"}), 400

    # 重複チェック
    existing = db.get_all_categories()
    if any(c.name == name for c in existing):
        return jsonify({"detail": "同じ名前のカテゴリが既にあります"}), 409

    # 並び順は末尾
    next_order = (max((c.sort_order for c in existing), default=0)) + 1
    cat = Category(
        id=str(uuid.uuid4()),
        name=name,
        emoji=(body.get("emoji") or "📦").strip(),
        color=(body.get("color") or "#9ca3af").strip(),
        sort_order=next_order,
    )
    return jsonify(db.add_category(cat).to_dict()), 201


@categories_bp.put("/<cat_id>")
@login_required
def edit_category(cat_id: str):
    body = request.get_json() or {}
    fields = {}
    if "name" in body:
        name = (body["name"] or "").strip()
        if not name:
            return jsonify({"detail": "カテゴリ名は空にできません"}), 400
        # 自分以外との重複チェック
        if any(c.name == name and c.id != cat_id for c in db.get_all_categories()):
            return jsonify({"detail": "同じ名前のカテゴリが既にあります"}), 409
        fields["name"] = name
    if "emoji" in body:
        fields["emoji"] = (body["emoji"] or "📦").strip()
    if "color" in body:
        fields["color"] = (body["color"] or "#9ca3af").strip()
    if not fields:
        return jsonify({"detail": "更新項目がありません"}), 400

    if not db.update_category(cat_id, fields):
        return jsonify({"detail": "カテゴリが見つかりません"}), 404
    return jsonify({"ok": True, **fields})


@categories_bp.delete("/<cat_id>")
@login_required
def remove_category(cat_id: str):
    if not db.delete_category(cat_id):
        return jsonify({"detail": "カテゴリが見つかりません"}), 404
    return "", 204
