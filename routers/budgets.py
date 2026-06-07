"""
予算管理APIルーター
  GET    /api/budgets?month=YYYY-MM   指定月の予算一覧
  POST   /api/budgets                 予算の設定・更新（upsert）
  DELETE /api/budgets/{id}            予算削除
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from datetime import date

import db

budgets_bp = Blueprint("budgets", __name__, url_prefix="/api/budgets")


@budgets_bp.get("")
@login_required
def list_budgets():
    # month 未指定なら今月
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    budgets = db.get_budgets(month)
    return jsonify([b.to_dict() for b in budgets])


@budgets_bp.post("")
@login_required
def upsert_budget():
    body = request.get_json() or {}
    category = (body.get("category") or "").strip()
    month = (body.get("month") or "").strip()
    if not category or not month:
        return jsonify({"detail": "category と month は必須です"}), 400
    try:
        amount = int(body.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"detail": "amount は数値で指定してください"}), 400

    # 0以下は予算解除（削除）として扱う
    if amount <= 0:
        for b in db.get_budgets(month):
            if b.category == category:
                db.delete_budget(b.id)
        return jsonify({"deleted": True, "category": category, "month": month})

    budget = db.upsert_budget(category, amount, month)
    return jsonify(budget.to_dict()), 201


@budgets_bp.delete("/<budget_id>")
@login_required
def remove_budget(budget_id: str):
    if not db.delete_budget(budget_id):
        return jsonify({"detail": "予算が見つかりません"}), 404
    return "", 204
