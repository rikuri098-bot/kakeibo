"""
パスワード検証・変更サービス
- 初期状態：.env の ADMIN_PASSWORD と平文比較
- パスワード変更後：Supabase settings テーブルに bcrypt ハッシュを保存し、以後はハッシュ照合
"""
import os
import bcrypt
import db

ADMIN_PASSWORD_ENV = os.getenv("ADMIN_PASSWORD", "password")
HASH_KEY = "admin_password_hash"


def verify_password(password: str) -> bool:
    """パスワードが正しいか検証する"""
    stored = db.get_setting(HASH_KEY)
    if stored:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
        except Exception:
            return False
    # まだ変更されていない場合は .env の値と比較
    return password == ADMIN_PASSWORD_ENV


def set_password(new_password: str):
    """新しいパスワードを bcrypt でハッシュ化して保存する"""
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.set_setting(HASH_KEY, hashed)
