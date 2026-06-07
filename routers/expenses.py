"""
支出API（ユーザーごとにスコープ）
  GET    /api/expenses        一覧
  POST   /api/expenses        追加
  PATCH  /api/expenses/{id}   更新
  DELETE /api/expenses/{id}   削除
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import uuid

from models import Expense
import db

expenses_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")


@expenses_bp.get("")
@login_required
def list_expenses():
    expenses = db.get_all_expenses(current_user.id)
    if not db.USE_SUPABASE:
        expenses = sorted(expenses, key=lambda e: (e.date, e.id), reverse=True)
    return jsonify([e.to_dict() for e in expenses])


@expenses_bp.post("")
@login_required
def create_expense():
    body = request.get_json()
    if not body:
        return jsonify({"detail": "リクエストボディが無効です"}), 400
    for key in ("date", "amount", "category", "payment_method"):
        if not body.get(key):
            return jsonify({"detail": f"{key} は必須です"}), 400

    new_expense = Expense(
        id=str(uuid.uuid4()),
        date=str(body["date"]),
        amount=int(body["amount"]),
        category=body["category"],
        payment_method=body["payment_method"],
        memo=body.get("memo", ""),
    )
    db.add_expense(current_user.id, new_expense)
    return jsonify(new_expense.to_dict()), 201


@expenses_bp.patch("/<expense_id>")
@login_required
def patch_expense(expense_id: str):
    body = request.get_json() or {}
    fields = {}
    for key in ("date", "category", "payment_method", "memo"):
        if key in body and body[key] is not None:
            fields[key] = body[key]
    if "amount" in body and body["amount"] is not None:
        fields["amount"] = int(body["amount"])
    if not fields:
        return jsonify({"detail": "更新項目がありません"}), 400
    if not db.update_expense(current_user.id, expense_id, fields):
        return jsonify({"detail": "支出データが見つかりません"}), 404
    return jsonify({"ok": True, **fields})


@expenses_bp.delete("/<expense_id>")
@login_required
def remove_expense(expense_id: str):
    if not db.delete_expense(current_user.id, expense_id):
        return jsonify({"detail": "支出データが見つかりません"}), 404
    return "", 204
