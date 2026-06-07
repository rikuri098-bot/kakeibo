"""
Flask-Login 用ユーザーモデル
Supabaseの users テーブルのレコードを表す。
"""
from flask_login import UserMixin


class User(UserMixin):
    """ログインユーザー（users テーブルに対応）"""

    def __init__(self, id: str, username: str, display_name: str = ""):
        self.id = id                      # Flask-Login が要求する id（= user_id）
        self.username = username
        self.display_name = display_name or username

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data["id"],
            username=data["username"],
            display_name=data.get("display_name", ""),
        )
