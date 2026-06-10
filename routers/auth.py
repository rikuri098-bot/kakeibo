"""
認証ルーター（複数ユーザー対応）
  GET/POST /login     ログイン
  GET/POST /register  新規登録（登録後は自動ログイン）
  GET      /logout    ログアウト
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from auth_models import User
from auth_utils import hash_password, check_password
import db

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login_page():
    return render_template("login.html")


@auth_bp.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    user = db.get_user_by_username(username)
    if user and check_password(password, user.get("password_hash", "")):
        login_user(User.from_dict(user), remember=True)
        next_url = request.args.get("next") or url_for("index")
        return redirect(next_url)

    flash("ユーザー名またはパスワードが違います", "error")
    return render_template("login.html"), 401


@auth_bp.get("/register")
def register_page():
    return render_template("register.html")


@auth_bp.post("/register")
def register_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    confirm  = request.form.get("confirm") or ""

    # バリデーション
    error = None
    if not username or not password:
        error = "ユーザー名とパスワードは必須です"
    elif len(username) < 3:
        error = "ユーザー名は3文字以上にしてください"
    elif len(password) < 6:
        error = "パスワードは6文字以上にしてください"
    elif password != confirm:
        error = "パスワード（確認）が一致しません"
    elif db.get_user_by_username(username):
        error = "このユーザー名は既に使われています"

    if error:
        flash(error, "error")
        return render_template("register.html", username=username), 400

    # ユーザー作成（表示名はユーザー名と同じ・デフォルトカテゴリも自動作成）＋自動ログイン
    user = db.create_user(username, hash_password(password), username)
    login_user(User.from_dict(user), remember=True)
    return redirect(url_for("index"))


@auth_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))


@auth_bp.delete("/api/auth/account")
@login_required
def delete_account():
    """ログイン中ユーザーの全データとアカウント自身を削除する"""
    user_id = current_user.id
    db.delete_account(user_id)
    logout_user()
    return jsonify({"ok": True, "message": "アカウントを削除しました"})
