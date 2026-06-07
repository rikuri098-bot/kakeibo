"""
データ永続化レイヤー
- SUPABASE_URL が .env にあれば → Supabase REST API
- なければ → JSONファイル（ローカル開発用）

expenses / categories / shortcuts の3テーブルを扱う。
移行時にこのファイルだけ書き換えればルーターへの影響はゼロ。
"""
import json
import os
import requests
from typing import List
from models import Expense, Category, Shortcut

# ── Supabase 接続設定 ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_ANON_KEY)

# ── JSONファイル設定（フォールバック用） ──────────────────────────
DATA_DIR = "data"
FILES = {
    "expenses":   os.path.join(DATA_DIR, "expenses.json"),
    "categories": os.path.join(DATA_DIR, "categories.json"),
    "shortcuts":  os.path.join(DATA_DIR, "shortcuts.json"),
}

# JSONモード時のカテゴリ初期値（Supabase未使用の開発環境用）
DEFAULT_CATEGORIES = [
    {"id": "seed-1", "name": "食費",   "emoji": "🛒", "color": "#34d399", "sort_order": 1},
    {"id": "seed-2", "name": "交通費", "emoji": "🚃", "color": "#60a5fa", "sort_order": 2},
    {"id": "seed-3", "name": "日用品", "emoji": "🧴", "color": "#fbbf24", "sort_order": 3},
    {"id": "seed-4", "name": "外食",   "emoji": "🍜", "color": "#fb923c", "sort_order": 4},
    {"id": "seed-5", "name": "娯楽",   "emoji": "🎮", "color": "#a78bfa", "sort_order": 5},
    {"id": "seed-6", "name": "その他", "emoji": "📦", "color": "#9ca3af", "sort_order": 6},
]


# ================================================================
# Supabase REST 共通ヘルパー
# ================================================================
def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _sb_select(table: str, params: dict) -> list:
    res = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb_headers(), params=params)
    res.raise_for_status()
    return res.json()


def _sb_insert(table: str, obj: dict) -> dict:
    res = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb_headers(), json=obj)
    res.raise_for_status()
    data = res.json()
    return data[0] if isinstance(data, list) and data else data


def _sb_update(table: str, row_id: str, obj: dict) -> dict:
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}",
                         headers=_sb_headers(), params={"id": f"eq.{row_id}"}, json=obj)
    res.raise_for_status()
    data = res.json()
    return data[0] if isinstance(data, list) and data else {}


def _sb_delete(table: str, row_id: str) -> bool:
    res = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}",
                          headers=_sb_headers(), params={"id": f"eq.{row_id}"})
    res.raise_for_status()
    return res.status_code in (200, 204)


# ================================================================
# JSON ファイル 共通ヘルパー
# ================================================================
def _json_load(table: str) -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = FILES[table]
    if not os.path.exists(path):
        # categories は初期値で作成、それ以外は空
        initial = DEFAULT_CATEGORIES if table == "categories" else []
        with open(path, "w", encoding="utf-8") as f:
            json.dump(initial, f, ensure_ascii=False, indent=2)
        return list(initial)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _json_save(table: str, rows: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FILES[table], "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


# ================================================================
# 支出（expenses）
# ================================================================
def get_all_expenses() -> List[Expense]:
    if USE_SUPABASE:
        rows = _sb_select("expenses", {
            "select": "id,date,amount,category,payment_method,memo",
            "order": "date.desc,id.desc",
        })
    else:
        rows = _json_load("expenses")
    return [Expense.from_dict(r) for r in rows]


def add_expense(expense: Expense) -> Expense:
    if USE_SUPABASE:
        return Expense.from_dict(_sb_insert("expenses", expense.to_dict()))
    rows = _json_load("expenses")
    rows.append(expense.to_dict())
    _json_save("expenses", rows)
    return expense


def update_expense(expense_id: str, fields: dict) -> bool:
    """支出の一部フィールドを更新（カテゴリ一括設定などで使用）"""
    if USE_SUPABASE:
        return bool(_sb_update("expenses", expense_id, fields))
    rows = _json_load("expenses")
    found = False
    for r in rows:
        if r["id"] == expense_id:
            r.update(fields)
            found = True
    if found:
        _json_save("expenses", rows)
    return found


def delete_expense(expense_id: str) -> bool:
    if USE_SUPABASE:
        return _sb_delete("expenses", expense_id)
    rows = _json_load("expenses")
    new_rows = [r for r in rows if r["id"] != expense_id]
    if len(new_rows) == len(rows):
        return False
    _json_save("expenses", new_rows)
    return True


# ================================================================
# カテゴリ（categories）
# ================================================================
def get_all_categories() -> List[Category]:
    if USE_SUPABASE:
        rows = _sb_select("categories", {
            "select": "id,name,emoji,color,sort_order",
            "order": "sort_order.asc,name.asc",
        })
        # Supabaseが空ならデフォルトを投入（初回のみ）
        if not rows:
            for c in DEFAULT_CATEGORIES:
                try:
                    _sb_insert("categories", c)
                except Exception:
                    pass
            rows = _sb_select("categories", {
                "select": "id,name,emoji,color,sort_order",
                "order": "sort_order.asc,name.asc",
            })
    else:
        rows = _json_load("categories")
        rows = sorted(rows, key=lambda c: (c.get("sort_order", 0), c.get("name", "")))
    return [Category.from_dict(r) for r in rows]


def add_category(cat: Category) -> Category:
    if USE_SUPABASE:
        return Category.from_dict(_sb_insert("categories", cat.to_dict()))
    rows = _json_load("categories")
    rows.append(cat.to_dict())
    _json_save("categories", rows)
    return cat


def update_category(cat_id: str, fields: dict) -> bool:
    if USE_SUPABASE:
        return bool(_sb_update("categories", cat_id, fields))
    rows = _json_load("categories")
    found = False
    for r in rows:
        if r["id"] == cat_id:
            r.update(fields)
            found = True
    if found:
        _json_save("categories", rows)
    return found


def delete_category(cat_id: str) -> bool:
    if USE_SUPABASE:
        return _sb_delete("categories", cat_id)
    rows = _json_load("categories")
    new_rows = [r for r in rows if r["id"] != cat_id]
    if len(new_rows) == len(rows):
        return False
    _json_save("categories", new_rows)
    return True


# ================================================================
# ショートカット（shortcuts）
# ================================================================
def get_all_shortcuts() -> List[Shortcut]:
    if USE_SUPABASE:
        rows = _sb_select("shortcuts", {
            "select": "id,label,amount,category,payment_method,memo,sort_order",
            "order": "sort_order.asc,id.asc",
        })
    else:
        rows = _json_load("shortcuts")
        rows = sorted(rows, key=lambda s: (s.get("sort_order", 0), s.get("id", "")))
    return [Shortcut.from_dict(r) for r in rows]


def add_shortcut(sc: Shortcut) -> Shortcut:
    if USE_SUPABASE:
        return Shortcut.from_dict(_sb_insert("shortcuts", sc.to_dict()))
    rows = _json_load("shortcuts")
    rows.append(sc.to_dict())
    _json_save("shortcuts", rows)
    return sc


def delete_shortcut(sc_id: str) -> bool:
    if USE_SUPABASE:
        return _sb_delete("shortcuts", sc_id)
    rows = _json_load("shortcuts")
    new_rows = [r for r in rows if r["id"] != sc_id]
    if len(new_rows) == len(rows):
        return False
    _json_save("shortcuts", new_rows)
    return True
