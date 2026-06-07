"""
認証ルーター
- GET  /login   ログインページ表示
- POST /login   ログイン処理
- GET  /logout  ログアウト
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from auth_models import AdminUser
import password_service

auth_bp = Blueprint("auth", __name__)

# .env から管理者ユーザー名を読み込む（パスワードは password_service が管理）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")


@auth_bp.get("/login")
def login_page():
    """ログインページを表示する"""
    return render_template("login.html")


@auth_bp.post("/login")
def login_post():
    """ログインフォームの処理"""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # ユーザー名・パスワードを検証（パスワードは bcrypt ハッシュ or .env）
    if username == ADMIN_USERNAME and password_service.verify_password(password):
        user = AdminUser(username)
        login_user(user, remember=True)
        # ログイン前にアクセスしていたページがあればそこへリダイレクト
        next_url = request.args.get("next") or url_for("index")
        return redirect(next_url)

    # 認証失敗
    flash("ユーザー名またはパスワードが違います", "error")
    return render_template("login.html"), 401


@auth_bp.get("/logout")
@login_required
def logout():
    """ログアウト処理"""
    logout_user()
    return redirect(url_for("auth.login_page"))
