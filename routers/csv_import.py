"""
PayPay カード取引履歴CSVインポートルーター
エンドポイント：
  POST /api/csv/import  - CSVファイルをアップロードして支出を一括登録
"""
import csv
import io
import uuid
import re
from flask import Blueprint, request, jsonify
from flask_login import login_required

from models import Expense
import db

csv_bp = Blueprint("csv", __name__, url_prefix="/api/csv")

# PayPay カード CSV のカラム名候補（バージョン差異に対応）
DATE_COLS    = ["ご利用日", "利用日", "date", "Date"]
AMOUNT_COLS  = ["ご利用金額（円）", "ご利用金額", "利用金額", "金額", "amount"]
STORE_COLS   = ["ご利用店名", "利用店名", "店名", "description", "Description"]
TYPE_COLS    = ["支払区分", "支払い区分", "種別", "type"]

# 金額が「チャージ」「入金」など収入系の場合はスキップ
SKIP_KEYWORDS = ["チャージ", "返金", "入金", "ポイント還元"]


def _find_col(headers: list[str], candidates: list[str]) -> str | None:
    """ヘッダーリストから候補列名を探して返す"""
    for c in candidates:
        if c in headers:
            return c
    return None


def _parse_amount(value: str) -> int | None:
    """金額文字列から数値を抽出（カンマ・円記号・マイナス符号対応）"""
    cleaned = re.sub(r"[^\d]", "", value)  # 数字以外を除去
    return int(cleaned) if cleaned else None


def _guess_category(store_name: str) -> str:
    """店名から支出カテゴリを推定する"""
    name = store_name.lower()
    if any(k in name for k in ["コンビニ", "セブン", "ファミマ", "ローソン", "ミニスト"]):
        return "食費"
    if any(k in name for k in ["スーパー", "イオン", "マルエツ", "西友", "ライフ", "食品"]):
        return "食費"
    if any(k in name for k in ["電車", "バス", "jr", "地下鉄", "交通", "suica", "pasmo"]):
        return "交通費"
    if any(k in name for k in ["ドラッグ", "薬局", "マツキヨ", "ツルハ", "ウェルシア"]):
        return "日用品"
    if any(k in name for k in ["レストラン", "食堂", "カフェ", "sushi", "焼肉", "ラーメン",
                                 "マクドナルド", "ケンタッキー", "吉野家", "すき家"]):
        return "外食"
    if any(k in name for k in ["映画", "cinema", "netflix", "spotify", "ゲーム", "アマゾン",
                                 "amazon", "娯楽", "book", "本屋"]):
        return "娯楽"
    return "その他"


@csv_bp.post("/import")
@login_required
def import_csv():
    """
    PayPay カード取引履歴CSVを解析して支出を一括登録する。
    重複（同一IDまたは同日・同金額・同店名）はスキップする。
    """
    if "file" not in request.files:
        return jsonify({"detail": "fileが見つかりません"}), 400

    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"detail": "CSVファイルを選択してください"}), 400

    # Shift-JIS → UTF-8 変換（PayPayのCSVはShift-JIS）
    raw = f.read()
    for encoding in ["shift_jis", "cp932", "utf-8-sig", "utf-8"]:
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        return jsonify({"detail": "CSVのエンコーディングを認識できませんでした"}), 400

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    # 列名を特定
    date_col   = _find_col(headers, DATE_COLS)
    amount_col = _find_col(headers, AMOUNT_COLS)
    store_col  = _find_col(headers, STORE_COLS)

    if not date_col or not amount_col:
        return jsonify({
            "detail": f"必須列が見つかりません。検出されたヘッダー: {headers}"
        }), 422

    # 既存データを取得して重複チェック用セットを作る
    existing = db.get_all_expenses()
    # (date, amount, memo) の組み合わせで重複判定
    existing_keys = {(e.date, e.amount, e.memo) for e in existing}

    added = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            date_raw   = (row.get(date_col) or "").strip()
            amount_raw = (row.get(amount_col) or "").strip()
            store_name = (row.get(store_col) or "").strip() if store_col else ""

            # スキップ対象（チャージ・返金など）
            if any(kw in store_name for kw in SKIP_KEYWORDS):
                skipped += 1
                continue

            # 日付を YYYY-MM-DD 形式に変換（YYYY/MM/DD → YYYY-MM-DD）
            date_str = date_raw.replace("/", "-")
            # 8桁yyyymmddにも対応
            if re.match(r"^\d{8}$", date_str):
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            amount = _parse_amount(amount_raw)
            if not amount or amount <= 0:
                skipped += 1
                continue

            memo = store_name or "CSV取込"

            # 重複チェック
            key = (date_str, amount, memo)
            if key in existing_keys:
                skipped += 1
                continue

            # 支出を追加
            new_expense = Expense(
                id=str(uuid.uuid4()),
                date=date_str,
                amount=amount,
                category=_guess_category(store_name),
                payment_method="PayPay",
                memo=memo,
            )
            db.add_expense(new_expense)
            existing_keys.add(key)
            added += 1

        except Exception as e:
            errors.append(f"行{i}: {str(e)}")

    return jsonify({
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "message": f"{added}件追加、{skipped}件スキップしました",
    })
