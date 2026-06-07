"""
データモデル定義
dataclassを使ってシンプルに管理する（Python 3.14対応・外部依存なし）
"""
from dataclasses import dataclass, field
from typing import Optional


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
        """dictに変換（JSON保存・レスポンス用）"""
        return {
            "id": self.id,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "payment_method": self.payment_method,
            "memo": self.memo,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Expense":
        """dictからExpenseを生成（JSON読み込み用）"""
        return cls(**data)
