"""
ショートカット管理APIルーター（よく使う支出のワンタップ登録）
  GET    /api/shortcuts        - 一覧
  POST   /api/shortcuts        - 追加
  DELETE /api/shortcuts/{id}   - 削除
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
import uuid

from models import Shortcut
import db

shortcuts_bp = Blueprint("shortcuts", __name__, url_prefix="/api/shortcuts")


@shortcuts_bp.get("")
@login_required
def list_shortcuts():
    items = db.get_all_shortcuts()
    return jsonify([s.to_dict() for s in items])


@shortcuts_bp.post("")
@login_required
def create_shortcut():
    body = request.get_json() or {}
    label = (body.get("label") or "").strip()
    if not label:
        return jsonify({"detail": "ラベルは必須です"}), 400

    existing = db.get_all_shortcuts()
    next_order = (max((s.sort_order for s in existing), default=0)) + 1
    sc = Shortcut(
        id=str(uuid.uuid4()),
        label=label,
        amount=int(body.get("amount") or 0),
        category=(body.get("category") or "").strip(),
        payment_method=(body.get("payment_method") or "PayPay").strip(),
        memo=(body.get("memo") or "").strip(),
        sort_order=next_order,
    )
    return jsonify(db.add_shortcut(sc).to_dict()), 201


@shortcuts_bp.delete("/<sc_id>")
@login_required
def remove_shortcut(sc_id: str):
    if not db.delete_shortcut(sc_id):
        return jsonify({"detail": "ショートカットが見つかりません"}), 404
    return "", 204
