"""
予算管理API（ユーザーごとにスコープ・デフォルト予算/繰り越し対応）
  GET    /api/budgets?month=YYYY-MM  実効予算（月次→なければデフォルト、繰り越し適用）
  GET    /api/budgets/default        デフォルト予算（month=NULL）
  POST   /api/budgets                upsert（is_default=trueでデフォルト保存・amount<=0で解除）
  DELETE /api/budgets/{id}
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import date

import db

budgets_bp = Blueprint("budgets", __name__, url_prefix="/api/budgets")


def _carryover_enabled(user_id: str) -> bool:
    return db.get_setting(user_id, "budget_carryover") == "total"


@budgets_bp.get("/default")
@login_required
def list_default_budgets():
    items = db.get_default_budgets(current_user.id)
    return jsonify({"budgets": [{"category": b.category, "amount": b.amount} for b in items]})


@budgets_bp.get("")
@login_required
def list_budgets():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    # raw=1 なら繰り越しを適用しない素の実効予算（編集フォーム用）
    raw = request.args.get("raw") == "1"
    enabled = (not raw) and _carryover_enabled(current_user.id)
    eff = db.get_effective_budgets(current_user.id, month, carryover=enabled)
    budgets = [{"category": c, "amount": a} for c, a in eff["map"].items()]
    return jsonify({
        "budgets": budgets,
        "carryover": eff["carryover"],
        "carryover_enabled": enabled,
        "month": month,
    })


@budgets_bp.post("")
@login_required
def upsert_budget():
    body = request.get_json() or {}
    category = (body.get("category") or "").strip()
    is_default = bool(body.get("is_default"))
    month = (body.get("month") or "").strip()
    if not category or (not is_default and not month):
        return jsonify({"detail": "category と month は必須です"}), 400
    try:
        amount = int(body.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"detail": "amount は数値で指定してください"}), 400

    # 0以下は解除（該当の月次 or デフォルトを削除）
    if amount <= 0:
        db.delete_budget_by_category(current_user.id, category,
                                     None if is_default else month, is_default)
        return jsonify({"deleted": True, "category": category, "is_default": is_default})

    budget = db.upsert_budget(current_user.id, category, amount,
                              None if is_default else month, is_default)
    return jsonify(budget.to_dict()), 201


@budgets_bp.delete("/<budget_id>")
@login_required
def remove_budget(budget_id: str):
    if not db.delete_budget(current_user.id, budget_id):
        return jsonify({"detail": "予算が見つかりません"}), 404
    return "", 204
