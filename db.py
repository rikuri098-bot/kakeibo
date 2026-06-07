"""
データ永続化レイヤー（複数ユーザー対応）
- SUPABASE_URL が .env にあれば → Supabase REST API
- なければ → JSONファイル（ローカル開発用）

すべてのデータ操作は user_id でスコープされ、他ユーザーのデータには触れない。
expenses / categories / shortcuts / budgets / settings / users を扱う。
"""
import json
import os
import uuid
import requests
from typing import List, Optional
from models import Expense, Category, Shortcut, Budget

# ── Supabase 接続設定 ──────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_ANON_KEY)

# ── JSONファイル設定（フォールバック用） ──────────────────────────
DATA_DIR = "data"
FILES = {
    "users":      os.path.join(DATA_DIR, "users.json"),
    "expenses":   os.path.join(DATA_DIR, "expenses.json"),
    "categories": os.path.join(DATA_DIR, "categories.json"),
    "shortcuts":  os.path.join(DATA_DIR, "shortcuts.json"),
    "budgets":    os.path.join(DATA_DIR, "budgets.json"),
    "settings":   os.path.join(DATA_DIR, "settings.json"),
}

# 新規ユーザー作成時に投入するデフォルトカテゴリ
DEFAULT_CATEGORIES = [
    {"name": "食費",   "emoji": "🛒", "color": "#34d399", "sort_order": 1},
    {"name": "交通費", "emoji": "🚃", "color": "#60a5fa", "sort_order": 2},
    {"name": "日用品", "emoji": "🧴", "color": "#fbbf24", "sort_order": 3},
    {"name": "外食",   "emoji": "🍜", "color": "#fb923c", "sort_order": 4},
    {"name": "娯楽",   "emoji": "🎮", "color": "#a78bfa", "sort_order": 5},
    {"name": "その他", "emoji": "📦", "color": "#9ca3af", "sort_order": 6},
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


def _sb_update(table: str, filters: dict, obj: dict) -> dict:
    """filters 例: {'id': 'eq.xxx', 'user_id': 'eq.yyy'}"""
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}",
                         headers=_sb_headers(), params=filters, json=obj)
    res.raise_for_status()
    data = res.json()
    return data[0] if isinstance(data, list) and data else {}


def _sb_delete(table: str, filters: dict) -> bool:
    res = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}",
                          headers=_sb_headers(), params=filters)
    res.raise_for_status()
    return res.status_code in (200, 204)


# ================================================================
# JSON ファイル 共通ヘルパー
# ================================================================
def _json_load(table: str) -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = FILES[table]
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _json_save(table: str, rows: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FILES[table], "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


# ================================================================
# ユーザー（users）
# ================================================================
def get_user_by_username(username: str) -> Optional[dict]:
    if USE_SUPABASE:
        rows = _sb_select("users", {
            "select": "id,username,password_hash,display_name", "username": f"eq.{username}"})
        return rows[0] if rows else None
    for u in _json_load("users"):
        if u.get("username") == username:
            return u
    return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    if USE_SUPABASE:
        rows = _sb_select("users", {
            "select": "id,username,password_hash,display_name", "id": f"eq.{user_id}"})
        return rows[0] if rows else None
    for u in _json_load("users"):
        if u.get("id") == user_id:
            return u
    return None


def set_user_password(user_id: str, password_hash: str) -> bool:
    """ユーザーのパスワードハッシュを更新する"""
    if USE_SUPABASE:
        return bool(_sb_update("users", {"id": f"eq.{user_id}"}, {"password_hash": password_hash}))
    rows = _json_load("users")
    found = False
    for u in rows:
        if u.get("id") == user_id:
            u["password_hash"] = password_hash; found = True
    if found:
        _json_save("users", rows)
    return found


def create_user(username: str, password_hash: str, display_name: str) -> dict:
    user = {
        "id": "usr-" + uuid.uuid4().hex[:12],
        "username": username,
        "password_hash": password_hash,
        "display_name": display_name or username,
    }
    if USE_SUPABASE:
        _sb_insert("users", user)
    else:
        rows = _json_load("users")
        rows.append(user)
        _json_save("users", rows)
    # 新規ユーザーにデフォルトカテゴリを作成
    seed_default_categories(user["id"])
    return user


# ================================================================
# 支出（expenses）— すべて user_id でスコープ
# ================================================================
def get_all_expenses(user_id: str) -> List[Expense]:
    if USE_SUPABASE:
        rows = _sb_select("expenses", {
            "select": "id,date,amount,category,payment_method,memo",
            "user_id": f"eq.{user_id}", "order": "date.desc,id.desc"})
    else:
        rows = [r for r in _json_load("expenses") if r.get("user_id") == user_id]
    return [Expense.from_dict(r) for r in rows]


def add_expense(user_id: str, expense: Expense) -> Expense:
    if USE_SUPABASE:
        row = _sb_insert("expenses", {**expense.to_dict(), "user_id": user_id})
        return Expense.from_dict(row)
    rows = _json_load("expenses")
    rows.append({**expense.to_dict(), "user_id": user_id})
    _json_save("expenses", rows)
    return expense


def update_expense(user_id: str, expense_id: str, fields: dict) -> bool:
    if USE_SUPABASE:
        return bool(_sb_update("expenses",
            {"id": f"eq.{expense_id}", "user_id": f"eq.{user_id}"}, fields))
    rows = _json_load("expenses")
    found = False
    for r in rows:
        if r["id"] == expense_id and r.get("user_id") == user_id:
            r.update(fields); found = True
    if found:
        _json_save("expenses", rows)
    return found


def delete_expense(user_id: str, expense_id: str) -> bool:
    if USE_SUPABASE:
        # 対象が存在するか確認してから削除（成否判定のため）
        exists = _sb_select("expenses", {
            "select": "id", "id": f"eq.{expense_id}", "user_id": f"eq.{user_id}"})
        if not exists:
            return False
        return _sb_delete("expenses", {"id": f"eq.{expense_id}", "user_id": f"eq.{user_id}"})
    rows = _json_load("expenses")
    new_rows = [r for r in rows if not (r["id"] == expense_id and r.get("user_id") == user_id)]
    if len(new_rows) == len(rows):
        return False
    _json_save("expenses", new_rows)
    return True


# ================================================================
# カテゴリ（categories）
# ================================================================
def seed_default_categories(user_id: str):
    """新規ユーザーにデフォルトカテゴリを作成する"""
    for c in DEFAULT_CATEGORIES:
        cat = {"id": "cat-" + uuid.uuid4().hex[:12], "user_id": user_id, **c}
        try:
            if USE_SUPABASE:
                _sb_insert("categories", cat)
            else:
                rows = _json_load("categories"); rows.append(cat); _json_save("categories", rows)
        except Exception:
            pass


def get_all_categories(user_id: str) -> List[Category]:
    if USE_SUPABASE:
        rows = _sb_select("categories", {
            "select": "id,name,emoji,color,sort_order",
            "user_id": f"eq.{user_id}", "order": "sort_order.asc,name.asc"})
    else:
        rows = sorted(
            [r for r in _json_load("categories") if r.get("user_id") == user_id],
            key=lambda c: (c.get("sort_order", 0), c.get("name", "")))
    return [Category.from_dict(r) for r in rows]


def add_category(user_id: str, cat: Category) -> Category:
    if USE_SUPABASE:
        return Category.from_dict(_sb_insert("categories", {**cat.to_dict(), "user_id": user_id}))
    rows = _json_load("categories")
    rows.append({**cat.to_dict(), "user_id": user_id})
    _json_save("categories", rows)
    return cat


def update_category(user_id: str, cat_id: str, fields: dict) -> bool:
    if USE_SUPABASE:
        return bool(_sb_update("categories",
            {"id": f"eq.{cat_id}", "user_id": f"eq.{user_id}"}, fields))
    rows = _json_load("categories")
    found = False
    for r in rows:
        if r["id"] == cat_id and r.get("user_id") == user_id:
            r.update(fields); found = True
    if found:
        _json_save("categories", rows)
    return found


def delete_category(user_id: str, cat_id: str) -> bool:
    if USE_SUPABASE:
        exists = _sb_select("categories", {
            "select": "id", "id": f"eq.{cat_id}", "user_id": f"eq.{user_id}"})
        if not exists:
            return False
        return _sb_delete("categories", {"id": f"eq.{cat_id}", "user_id": f"eq.{user_id}"})
    rows = _json_load("categories")
    new_rows = [r for r in rows if not (r["id"] == cat_id and r.get("user_id") == user_id)]
    if len(new_rows) == len(rows):
        return False
    _json_save("categories", new_rows)
    return True


# ================================================================
# ショートカット（shortcuts）
# ================================================================
def get_all_shortcuts(user_id: str) -> List[Shortcut]:
    if USE_SUPABASE:
        rows = _sb_select("shortcuts", {
            "select": "id,label,emoji,amount,category,payment_method,memo,sort_order",
            "user_id": f"eq.{user_id}", "order": "sort_order.asc,id.asc"})
    else:
        rows = sorted(
            [r for r in _json_load("shortcuts") if r.get("user_id") == user_id],
            key=lambda s: (s.get("sort_order", 0), s.get("id", "")))
    return [Shortcut.from_dict(r) for r in rows]


def add_shortcut(user_id: str, sc: Shortcut) -> Shortcut:
    if USE_SUPABASE:
        return Shortcut.from_dict(_sb_insert("shortcuts", {**sc.to_dict(), "user_id": user_id}))
    rows = _json_load("shortcuts")
    rows.append({**sc.to_dict(), "user_id": user_id})
    _json_save("shortcuts", rows)
    return sc


def update_shortcut(user_id: str, sc_id: str, fields: dict) -> bool:
    if USE_SUPABASE:
        return bool(_sb_update("shortcuts",
            {"id": f"eq.{sc_id}", "user_id": f"eq.{user_id}"}, fields))
    rows = _json_load("shortcuts")
    found = False
    for r in rows:
        if r["id"] == sc_id and r.get("user_id") == user_id:
            r.update(fields); found = True
    if found:
        _json_save("shortcuts", rows)
    return found


def delete_shortcut(user_id: str, sc_id: str) -> bool:
    if USE_SUPABASE:
        exists = _sb_select("shortcuts", {
            "select": "id", "id": f"eq.{sc_id}", "user_id": f"eq.{user_id}"})
        if not exists:
            return False
        return _sb_delete("shortcuts", {"id": f"eq.{sc_id}", "user_id": f"eq.{user_id}"})
    rows = _json_load("shortcuts")
    new_rows = [r for r in rows if not (r["id"] == sc_id and r.get("user_id") == user_id)]
    if len(new_rows) == len(rows):
        return False
    _json_save("shortcuts", new_rows)
    return True


# ================================================================
# 予算（budgets）
# ================================================================
def get_budgets(user_id: str, month: str) -> List[Budget]:
    if USE_SUPABASE:
        rows = _sb_select("budgets", {
            "select": "id,category,amount,month",
            "user_id": f"eq.{user_id}", "month": f"eq.{month}"})
    else:
        rows = [b for b in _json_load("budgets")
                if b.get("user_id") == user_id and b.get("month") == month]
    return [Budget.from_dict(r) for r in rows]


def upsert_budget(user_id: str, category: str, amount: int, month: str) -> Budget:
    if USE_SUPABASE:
        existing = _sb_select("budgets", {
            "select": "id", "user_id": f"eq.{user_id}",
            "category": f"eq.{category}", "month": f"eq.{month}"})
        if existing:
            _sb_update("budgets",
                {"id": f"eq.{existing[0]['id']}", "user_id": f"eq.{user_id}"}, {"amount": amount})
            return Budget(id=existing[0]["id"], category=category, amount=amount, month=month)
        row = _sb_insert("budgets", {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "category": category, "amount": amount, "month": month})
        return Budget.from_dict(row)
    rows = _json_load("budgets")
    for r in rows:
        if r.get("user_id") == user_id and r.get("category") == category and r.get("month") == month:
            r["amount"] = amount; _json_save("budgets", rows); return Budget.from_dict(r)
    new = {"id": str(uuid.uuid4()), "user_id": user_id,
           "category": category, "amount": amount, "month": month}
    rows.append(new); _json_save("budgets", rows)
    return Budget.from_dict(new)


def delete_budget(user_id: str, budget_id: str) -> bool:
    if USE_SUPABASE:
        exists = _sb_select("budgets", {
            "select": "id", "id": f"eq.{budget_id}", "user_id": f"eq.{user_id}"})
        if not exists:
            return False
        return _sb_delete("budgets", {"id": f"eq.{budget_id}", "user_id": f"eq.{user_id}"})
    rows = _json_load("budgets")
    new_rows = [r for r in rows if not (r["id"] == budget_id and r.get("user_id") == user_id)]
    if len(new_rows) == len(rows):
        return False
    _json_save("budgets", new_rows)
    return True


# ================================================================
# 設定（settings）キーバリュー（user_id + key）
# ================================================================
def get_setting(user_id: str, key: str):
    if USE_SUPABASE:
        rows = _sb_select("settings", {
            "select": "key,value", "user_id": f"eq.{user_id}", "key": f"eq.{key}"})
        return rows[0]["value"] if rows else None
    for s in _json_load("settings"):
        if s.get("user_id") == user_id and s.get("key") == key:
            return s.get("value")
    return None


def get_all_settings(user_id: str) -> dict:
    if USE_SUPABASE:
        rows = _sb_select("settings", {"select": "key,value", "user_id": f"eq.{user_id}"})
    else:
        rows = [s for s in _json_load("settings") if s.get("user_id") == user_id]
    return {r["key"]: r["value"] for r in rows}


def set_setting(user_id: str, key: str, value: str):
    if USE_SUPABASE:
        existing = _sb_select("settings", {
            "select": "key", "user_id": f"eq.{user_id}", "key": f"eq.{key}"})
        if existing:
            _sb_update("settings", {"user_id": f"eq.{user_id}", "key": f"eq.{key}"}, {"value": value})
        else:
            _sb_insert("settings", {"user_id": user_id, "key": key, "value": value})
        return
    rows = _json_load("settings")
    for s in rows:
        if s.get("user_id") == user_id and s.get("key") == key:
            s["value"] = value; _json_save("settings", rows); return
    rows.append({"user_id": user_id, "key": key, "value": value})
    _json_save("settings", rows)
