"""
支出関連APIルーター（Flask Blueprint版）
エンドポイント：
  GET    /api/expenses        - 全支出一覧取得
  POST   /api/expenses        - 支出追加
  DELETE /api/expenses/{id}   - 支出削除
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
import uuid

from models import Expense
import db

expenses_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")


@expenses_bp.get("")
@login_required
def list_expenses():
    """全支出を新しい順（日付降順）で返す"""
    expenses = db.get_all_expenses()
    # JSONファイルモードのみソートが必要（Supabaseはクエリでソート済み）
    if not db.USE_SUPABASE:
        expenses = sorted(expenses, key=lambda e: (e.date, e.id), reverse=True)
    return jsonify([e.to_dict() for e in expenses])


@expenses_bp.post("")
@login_required
def create_expense():
    """新しい支出を追加する"""
    body = request.get_json()
    if not body:
        return jsonify({"detail": "リクエストボディが無効です"}), 400

    # 必須項目のバリデーション
    required = ["date", "amount", "category", "payment_method"]
    for key in required:
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
    db.add_expense(new_expense)
    return jsonify(new_expense.to_dict()), 201


@expenses_bp.delete("/<expense_id>")
@login_required
def remove_expense(expense_id: str):
    """指定IDの支出を削除する"""
    success = db.delete_expense(expense_id)
    if not success:
        return jsonify({"detail": "支出データが見つかりません"}), 404
    return "", 204
