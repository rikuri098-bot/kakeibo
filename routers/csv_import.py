"""
PayPay カード取引履歴CSVインポートルーター
エンドポイント：
  POST /api/csv/import  - CSVファイルをアップロードして支出を一括登録

対応フォーマット（新旧両対応）：
  ■ 新形式（明細ダウンロード）:
     取引日, 出金金額（円）, 入金金額（円）, 海外出金金額, 通貨, 変換レート（円）,
     利用国, 取引内容, 取引先, 取引方法, 支払い区分, 利用者, 取引番号
  ■ 旧形式（取引履歴）:
     ご利用日, ご利用店名, 支払区分, ご利用金額（円）, 支払回数
"""
import csv
import io
import uuid
import re
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models import Expense
import db

csv_bp = Blueprint("csv", __name__, url_prefix="/api/csv")

# ── カラム名の候補（新形式を優先的に先頭へ） ──────────────────────
DATE_COLS    = ["取引日", "ご利用日", "利用日", "date", "Date"]
# 出金金額（円）= 新形式の支出額。旧形式のご利用金額も候補に含める。
AMOUNT_COLS  = ["出金金額（円）", "出金金額", "ご利用金額（円）", "ご利用金額", "利用金額", "金額", "amount"]
# 取引先 = 新形式の店名。旧形式のご利用店名も候補に。
STORE_COLS   = ["取引先", "ご利用店名", "利用店名", "店名", "description", "Description"]
# 取引内容 = カテゴリ推定の主材料（新形式）
CONTENT_COLS = ["取引内容", "内容"]

# 収入・チャージ系のキーワード（支出ではないのでスキップ）
SKIP_KEYWORDS = ["チャージ", "オートチャージ", "返金", "入金", "ポイント還元",
                 "キャッシュバック", "残高", "送金受取"]


def _find_col(headers: list[str], candidates: list[str]) -> str | None:
    """ヘッダーリストから候補列名を探して返す"""
    for c in candidates:
        if c in headers:
            return c
    return None


def _parse_amount(value: str) -> int | None:
    """金額文字列から数値を抽出（カンマ・円記号対応、マイナスは負値で返す）"""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # マイナス表記（-, −, ▲, △）を検出
    is_negative = s[0] in ("-", "−", "▲", "△")
    cleaned = re.sub(r"[^\d]", "", s)  # 数字以外を除去
    if not cleaned:
        return None
    amount = int(cleaned)
    return -amount if is_negative else amount


def _guess_category(text: str) -> str:
    """取引内容・店名からカテゴリを推定する（既存ロジックを流用）"""
    name = (text or "").lower()
    if any(k in name for k in ["コンビニ", "セブン", "ファミマ", "ファミリーマート",
                                 "ローソン", "ミニストップ", "デイリー"]):
        return "食費"
    if any(k in name for k in ["スーパー", "イオン", "マルエツ", "西友", "ライフ",
                                 "サミット", "成城石井", "食品", "ストア", "マート"]):
        return "食費"
    if any(k in name for k in ["電車", "バス", "jr", "地下鉄", "メトロ", "鉄道", "交通",
                                 "suica", "pasmo", "タクシー", "高速", "etc"]):
        return "交通費"
    if any(k in name for k in ["ドラッグ", "薬局", "マツキヨ", "マツモトキヨシ", "ツルハ",
                                 "ウエルシア", "ウェルシア", "サンドラッグ", "コクミン",
                                 "薬", "ダイソー", "百均", "ニトリ", "無印"]):
        return "日用品"
    if any(k in name for k in ["レストラン", "食堂", "カフェ", "cafe", "sushi", "寿司",
                                 "焼肉", "ラーメン", "うどん", "そば", "居酒屋", "バル",
                                 "マクドナルド", "ケンタッキー", "モスバーガー", "スターバックス",
                                 "スタバ", "ドトール", "タリーズ", "吉野家", "すき家", "松屋",
                                 "ガスト", "サイゼ", "牛丼", "ピザ", "バーガー"]):
        return "外食"
    if any(k in name for k in ["映画", "cinema", "シネマ", "netflix", "spotify", "youtube",
                                 "ゲーム", "game", "amazon", "アマゾン", "楽天", "娯楽",
                                 "book", "本屋", "書店", "カラオケ", "ライブ", "コンサート",
                                 "dアニメ", "hulu", "disney", "apple"]):
        return "娯楽"
    # どのキーワードにも一致しない場合は「未分類」とし、後でユーザーが設定する
    return "未分類"


@csv_bp.post("/import")
@login_required
def import_csv():
    """
    PayPay カード取引履歴CSVを解析して支出を一括登録する。
    重複（同日・同金額・同店名）はスキップする。
    """
    if "file" not in request.files:
        return jsonify({"detail": "fileが見つかりません"}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return jsonify({"detail": "CSVファイルを選択してください"}), 400

    # 文字コード自動判定（PayPayはShift-JIS/UTF-8どちらもあり得る）
    raw = f.read()
    text = None
    for encoding in ["utf-8-sig", "shift_jis", "cp932", "utf-8"]:
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        return jsonify({"detail": "CSVのエンコーディングを認識できませんでした"}), 400

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    # 列名を特定
    date_col    = _find_col(headers, DATE_COLS)
    amount_col  = _find_col(headers, AMOUNT_COLS)
    store_col   = _find_col(headers, STORE_COLS)
    content_col = _find_col(headers, CONTENT_COLS)

    if not date_col or not amount_col:
        return jsonify({
            "detail": f"必須列（日付・金額）が見つかりません。検出ヘッダー: {headers}"
        }), 422

    # 新形式（出金金額（円）または取引内容あり）なら支払い方法は「PayPayカード」固定
    is_new_format = (amount_col in ("出金金額（円）", "出金金額")) or (content_col is not None)
    payment_method = "PayPayカード" if is_new_format else "PayPay"

    # 既存データを取得して重複チェック用セットを作る（date, amount, memo）
    existing = db.get_all_expenses(current_user.id)
    existing_keys = {(e.date, e.amount, e.memo) for e in existing}

    added = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            date_raw   = (row.get(date_col) or "").strip()
            amount_raw = (row.get(amount_col) or "").strip()
            store_name = (row.get(store_col) or "").strip() if store_col else ""
            content    = (row.get(content_col) or "").strip() if content_col else ""

            # 日付が空の行はスキップ（合計行など）
            if not date_raw:
                skipped += 1
                continue

            # 金額を解析：空欄・0・マイナス（=入金/返金）はスキップ
            amount = _parse_amount(amount_raw)
            if not amount or amount <= 0:
                skipped += 1
                continue

            # チャージ・返金などのキーワードを含む行はスキップ
            check_text = f"{content} {store_name}"
            if any(kw in check_text for kw in SKIP_KEYWORDS):
                skipped += 1
                continue

            # 日付を YYYY-MM-DD 形式へ正規化
            date_str = date_raw.replace("/", "-")
            if re.match(r"^\d{8}$", date_str):  # yyyymmdd 形式にも対応
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # メモは取引先（なければ取引内容）
            memo = store_name or content or "CSV取込"

            # 重複チェック
            key = (date_str, amount, memo)
            if key in existing_keys:
                skipped += 1
                continue

            # カテゴリ推定（取引内容＋取引先の両方を材料にする）
            category = _guess_category(f"{content} {store_name}")

            new_expense = Expense(
                id=str(uuid.uuid4()),
                date=date_str,
                amount=amount,
                category=category,
                payment_method=payment_method,
                memo=memo,
            )
            db.add_expense(current_user.id, new_expense)
            existing_keys.add(key)
            added += 1

        except Exception as e:
            errors.append(f"行{i}: {str(e)}")

    return jsonify({
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "format": "新形式" if is_new_format else "旧形式",
        "message": f"{added}件追加、{skipped}件スキップしました",
    })
