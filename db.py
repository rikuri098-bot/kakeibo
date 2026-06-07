"""
データ永続化レイヤー
- SUPABASE_URL が .env に設定されている場合 → Supabase REST API を使用
- 未設定の場合 → JSONファイルにフォールバック（ローカル開発用）

移行時にこのファイルだけ書き換えればAPIルーターへの影響はゼロ。
"""
import json
import os
import requests
from typing import List
from models import Expense

# ── Supabase 接続設定 ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_ANON_KEY)

# ── JSONファイル設定（フォールバック用） ──────────────────────────
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "expenses.json")


# ================================================================
# 公開API（ルーターから呼ぶ関数。Supabase/JSON 共通インターフェース）
# ================================================================

def get_all_expenses() -> List[Expense]:
    """全支出データを取得する"""
    if USE_SUPABASE:
        return _supabase_get_all()
    return _json_get_all()


def add_expense(expense: Expense) -> Expense:
    """支出データを追加する"""
    if USE_SUPABASE:
        return _supabase_add(expense)
    return _json_add(expense)


def delete_expense(expense_id: str) -> bool:
    """指定IDの支出を削除する。成功したら True を返す"""
    if USE_SUPABASE:
        return _supabase_delete(expense_id)
    return _json_delete(expense_id)


def get_expense_by_id(expense_id: str):
    """IDで支出を1件取得（重複チェック用）"""
    if USE_SUPABASE:
        return _supabase_get_by_id(expense_id)
    expenses = _json_get_all()
    return next((e for e in expenses if e.id == expense_id), None)


# ================================================================
# Supabase REST API 実装
# ================================================================

def _sb_headers() -> dict:
    """Supabase APIリクエスト用ヘッダー"""
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",  # INSERT/UPDATE 後にレコードを返す
    }


def _supabase_get_all() -> List[Expense]:
    """Supabase から全支出を取得（日付降順）"""
    url = f"{SUPABASE_URL}/rest/v1/expenses"
    res = requests.get(url, headers=_sb_headers(), params={
        "select": "id,date,amount,category,payment_method,memo",
        "order": "date.desc,id.desc",
    })
    res.raise_for_status()
    return [Expense.from_dict(row) for row in res.json()]


def _supabase_add(expense: Expense) -> Expense:
    """Supabase に支出を1件追加する"""
    url = f"{SUPABASE_URL}/rest/v1/expenses"
    res = requests.post(url, headers=_sb_headers(), json=expense.to_dict())
    res.raise_for_status()
    data = res.json()
    # Prefer: return=representation の場合リストで返ってくる
    row = data[0] if isinstance(data, list) else data
    return Expense.from_dict(row)


def _supabase_delete(expense_id: str) -> bool:
    """Supabase から指定IDの支出を削除する"""
    url = f"{SUPABASE_URL}/rest/v1/expenses"
    res = requests.delete(url, headers=_sb_headers(), params={
        "id": f"eq.{expense_id}",
    })
    res.raise_for_status()
    return res.status_code in (200, 204)


def _supabase_get_by_id(expense_id: str):
    """Supabase からIDで1件取得"""
    url = f"{SUPABASE_URL}/rest/v1/expenses"
    res = requests.get(url, headers=_sb_headers(), params={
        "id": f"eq.{expense_id}",
        "select": "*",
    })
    res.raise_for_status()
    rows = res.json()
    return Expense.from_dict(rows[0]) if rows else None


# ================================================================
# JSON ファイル実装（フォールバック）
# ================================================================

def _ensure_data_dir():
    """data/ ディレクトリとJSONファイルを初期化"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _json_get_all() -> List[Expense]:
    _ensure_data_dir()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Expense.from_dict(item) for item in data]


def _json_add(expense: Expense) -> Expense:
    _ensure_data_dir()
    expenses = _json_get_all()
    expenses.append(expense)
    _save_json(expenses)
    return expense


def _json_delete(expense_id: str) -> bool:
    expenses = _json_get_all()
    new_list = [e for e in expenses if e.id != expense_id]
    if len(new_list) == len(expenses):
        return False
    _save_json(new_list)
    return True


def _save_json(expenses: List[Expense]):
    """支出リストをJSONファイルに書き込む"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in expenses], f, ensure_ascii=False, indent=2)
