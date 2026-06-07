"""
設定APIルーター（通知設定・パスワード変更）
  GET  /api/settings              通知設定の取得
  PUT  /api/settings              通知設定の更新
  POST /api/settings/password     パスワード変更（bcryptハッシュをsettingsに保存）
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

import db
import password_service

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

# 通知設定の既定値
DEFAULTS = {
    "always_show_remaining": "false",  # 残り予算を常時表示するか
    "notify_threshold": "20",          # 残り何%で通知するか
}


@settings_bp.get("")
@login_required
def get_settings():
    """通知設定を取得する（パスワードハッシュは含めない）"""
    stored = db.get_all_settings()
    result = dict(DEFAULTS)
    for k in DEFAULTS:
        if k in stored and stored[k] is not None:
            result[k] = stored[k]
    return jsonify(result)


@settings_bp.put("")
@login_required
def update_settings():
    """通知設定を更新する"""
    body = request.get_json() or {}
    if "always_show_remaining" in body:
        val = body["always_show_remaining"]
        db.set_setting("always_show_remaining", "true" if val in (True, "true", 1) else "false")
    if "notify_threshold" in body:
        try:
            th = int(body["notify_threshold"])
            if th in (5, 10, 20):
                db.set_setting("notify_threshold", str(th))
        except (TypeError, ValueError):
            pass
    return jsonify({"ok": True})


@settings_bp.post("/password")
@login_required
def change_password():
    """パスワードを変更する（bcryptハッシュをsettingsへ保存）"""
    body = request.get_json() or {}
    current = body.get("current") or ""
    new = body.get("new") or ""
    confirm = body.get("confirm") or ""

    if not password_service.verify_password(current):
        return jsonify({"detail": "現在のパスワードが違います"}), 400
    if len(new) < 6:
        return jsonify({"detail": "新しいパスワードは6文字以上にしてください"}), 400
    if new != confirm:
        return jsonify({"detail": "新しいパスワード（確認）が一致しません"}), 400

    password_service.set_password(new)
    return jsonify({"ok": True, "message": "パスワードを変更しました"})
