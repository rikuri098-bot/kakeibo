"""
Flask-Login 用ユーザーモデル
シンプルな管理者ユーザー1名のみ。DBは使わない。
"""
from flask_login import UserMixin


class AdminUser(UserMixin):
    """管理者ユーザークラス（.envの認証情報に対応）"""

    def __init__(self, username: str):
        self.id = username       # Flask-Login が要求する id プロパティ
        self.username = username
