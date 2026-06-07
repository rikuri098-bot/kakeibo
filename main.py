"""
家計簿アプリ エントリーポイント（Flask + Flask-Login版）
起動方法: python main.py
アクセス: http://localhost:8000
"""
import os
from flask import Flask, send_from_directory, redirect, url_for
from flask_login import LoginManager, login_required
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（インポートより先に実行）
load_dotenv()

from auth_models import AdminUser
from routers.expenses import expenses_bp
from routers.auth import auth_bp
from routers.csv_import import csv_bp

# ── Flask アプリ初期化 ────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ── Flask-Login 初期化 ────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login_page"      # 未ログイン時のリダイレクト先
login_manager.login_message = "ログインが必要です"

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

@login_manager.user_loader
def load_user(user_id: str):
    """セッションからユーザーを復元する（Flask-Login が呼び出す）"""
    if user_id == ADMIN_USERNAME:
        return AdminUser(user_id)
    return None

# ── Blueprint 登録 ────────────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(csv_bp)


@app.route("/")
@login_required
def index():
    """トップページ（未ログイン時は自動で /login にリダイレクト）"""
    return send_from_directory("static", "index.html")


# ── 起動 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"サーバー起動中... http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
