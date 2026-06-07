"""
設定API（ユーザーごとにスコープ：通知設定・パスワード変更）
  GET  /api/settings              通知設定の取得
  PUT  /api/settings              通知設定の更新
  POST /api/settings/password     パスワード変更（users.password_hash を更新）
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

import db
from auth_utils import hash_password, check_password

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

DEFAULTS = {
    "always_show_remaining": "false",
    "notify_threshold": "20",
}


@settings_bp.get("")
@login_required
def get_settings():
    stored = db.get_all_settings(current_user.id)
    result = dict(DEFAULTS)
    for k in DEFAULTS:
        if k in stored and stored[k] is not None:
            result[k] = stored[k]
    return jsonify(result)


@settings_bp.put("")
@login_required
def update_settings():
    body = request.get_json() or {}
    if "always_show_remaining" in body:
        val = body["always_show_remaining"]
        db.set_setting(current_user.id, "always_show_remaining",
                       "true" if val in (True, "true", 1) else "false")
    if "notify_threshold" in body:
        try:
            th = int(body["notify_threshold"])
            if th in (5, 10, 20):
                db.set_setting(current_user.id, "notify_threshold", str(th))
        except (TypeError, ValueError):
            pass
    return jsonify({"ok": True})


@settings_bp.post("/password")
@login_required
def change_password():
    body = request.get_json() or {}
    current = body.get("current") or ""
    new = body.get("new") or ""
    confirm = body.get("confirm") or ""

    user = db.get_user_by_id(current_user.id)
    if not user or not check_password(current, user.get("password_hash", "")):
        return jsonify({"detail": "現在のパスワードが違います"}), 400
    if len(new) < 6:
        return jsonify({"detail": "新しいパスワードは6文字以上にしてください"}), 400
    if new != confirm:
        return jsonify({"detail": "新しいパスワード（確認）が一致しません"}), 400

    # users テーブルの password_hash を更新（bcrypt）
    db.set_user_password(current_user.id, hash_password(new))
    return jsonify({"ok": True, "message": "パスワードを変更しました"})
