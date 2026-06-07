"""
パスワードのハッシュ化・照合（bcrypt）
"""
import bcrypt


def hash_password(password: str) -> str:
    """平文パスワードを bcrypt でハッシュ化する"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    """平文パスワードがハッシュと一致するか検証する"""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False
