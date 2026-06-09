"""
データモデル定義
dataclassでシンプルに管理する（Python 3.14対応・外部依存なし）
Supabaseが返す created_at など余分なカラムは from_dict で自動的に無視する。
"""
from dataclasses import dataclass, fields
from typing import Optional


def _from_dict(cls, data: dict):
    """共通: 既知のフィールドだけ拾ってインスタンス化する"""
    allowed = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class Expense:
    """支出データモデル"""
    id: str
    date: str               # 日付（ISO文字列 例: 2026-06-01）
    amount: int             # 金額（円）
    category: str           # カテゴリ
    payment_method: str     # 支払い方法
    memo: str = ""          # メモ（任意）

    def to_dict(self) -> dict:
        return {
            "id": self.id, "date": self.date, "amount": self.amount,
            "category": self.category, "payment_method": self.payment_method,
            "memo": self.memo,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Expense":
        return _from_dict(cls, data)


@dataclass
class Category:
    """ユーザー定義カテゴリ"""
    id: str
    name: str                   # カテゴリ名（例: 食費）
    emoji: str = "📦"           # 絵文字アイコン
    color: str = "#9ca3af"      # 表示色（hex）
    sort_order: int = 0         # 並び順

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "emoji": self.emoji,
            "color": self.color, "sort_order": self.sort_order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        return _from_dict(cls, data)


@dataclass
class Budget:
    """予算（カテゴリ別 or 全体合計）"""
    id: str
    category: str               # カテゴリ名 または 'total'（全体合計）
    amount: int                 # 月の予算額（円）
    month: Optional[str] = None # 対象月（YYYY-MM）。デフォルト予算は None
    is_default: bool = False    # デフォルト予算かどうか

    def to_dict(self) -> dict:
        return {"id": self.id, "category": self.category, "amount": self.amount,
                "month": self.month, "is_default": self.is_default}

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return _from_dict(cls, data)


@dataclass
class Shortcut:
    """よく使う支出のワンタップ・ショートカット"""
    id: str
    label: str                      # 表示ラベル（例: コンビニ）
    emoji: str = "⚡"               # アイコン絵文字
    amount: int = 0                 # 既定金額（0なら入力時に確認）
    category: str = ""              # カテゴリ
    payment_method: str = "PayPay"  # 支払い方法
    memo: str = ""                  # メモ
    sort_order: int = 0             # 並び順

    def to_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "emoji": self.emoji,
            "amount": self.amount, "category": self.category,
            "payment_method": self.payment_method,
            "memo": self.memo, "sort_order": self.sort_order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Shortcut":
        return _from_dict(cls, data)
