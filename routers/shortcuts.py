"""
ショートカット管理API（ユーザーごとにスコープ）
  GET    /api/shortcuts
  POST   /api/shortcuts
  PUT    /api/shortcuts/{id}      ラベル・金額・カテゴリ・絵文字・並び順の更新
  DELETE /api/shortcuts/{id}
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import uuid

from models import Shortcut
import db

shortcuts_bp = Blueprint("shortcuts", __name__, url_prefix="/api/shortcuts")


@shortcuts_bp.get("")
@login_required
def list_shortcuts():
    return jsonify([s.to_dict() for s in db.get_all_shortcuts(current_user.id)])


@shortcuts_bp.post("")
@login_required
def create_shortcut():
    body = request.get_json() or {}
    label = (body.get("label") or "").strip()
    if not label:
        return jsonify({"detail": "ラベルは必須です"}), 400

    existing = db.get_all_shortcuts(current_user.id)
    next_order = (max((s.sort_order for s in existing), default=0)) + 1
    sc = Shortcut(
        id=str(uuid.uuid4()),
        label=label,
        emoji=(body.get("emoji") or "⚡").strip(),
        amount=int(body.get("amount") or 0),
        category=(body.get("category") or "").strip(),
        payment_method=(body.get("payment_method") or "PayPay").strip(),
        memo=(body.get("memo") or "").strip(),
        sort_order=next_order,
    )
    return jsonify(db.add_shortcut(current_user.id, sc).to_dict()), 201


@shortcuts_bp.put("/<sc_id>")
@login_required
def edit_shortcut(sc_id: str):
    body = request.get_json() or {}
    fields = {}
    if "label" in body:
        label = (body["label"] or "").strip()
        if not label:
            return jsonify({"detail": "ラベルは空にできません"}), 400
        fields["label"] = label
    if "emoji" in body:
        fields["emoji"] = (body["emoji"] or "⚡").strip()
    if "memo" in body:
        fields["memo"] = (body["memo"] or "").strip()
    if "category" in body:
        fields["category"] = (body["category"] or "").strip()
    if "payment_method" in body:
        fields["payment_method"] = (body["payment_method"] or "PayPay").strip()
    if "amount" in body:
        try:
            fields["amount"] = int(body["amount"] or 0)
        except (TypeError, ValueError):
            pass
    if "sort_order" in body:
        try:
            fields["sort_order"] = int(body["sort_order"])
        except (TypeError, ValueError):
            pass
    if not fields:
        return jsonify({"detail": "更新項目がありません"}), 400
    if not db.update_shortcut(current_user.id, sc_id, fields):
        return jsonify({"detail": "ショートカットが見つかりません"}), 404
    return jsonify({"ok": True, **fields})


@shortcuts_bp.delete("/<sc_id>")
@login_required
def remove_shortcut(sc_id: str):
    if not db.delete_shortcut(current_user.id, sc_id):
        return jsonify({"detail": "ショートカットが見つかりません"}), 404
    return "", 204
