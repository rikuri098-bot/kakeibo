# 家計簿アプリ

ローカル＆クラウドで動くシンプルな家計簿Webアプリです。
Flask + Supabase + Vercel で構成され、ログイン認証・PayPay CSVインポートに対応しています。

## 🌐 本番URL

https://kakeibo-blond-six.vercel.app

ログイン情報は `.env` の `ADMIN_USERNAME` / `ADMIN_PASSWORD` で管理しています。

## フォルダ構成

```
kakeibo/
├── main.py              # Flaskエントリーポイント・起動ファイル
├── models.py            # データモデル定義（dataclass）
├── db.py                # データ永続化レイヤー（JSON/Supabase 自動切替）
├── auth_models.py       # Flask-Login用ユーザーモデル
├── setup_db.py          # Supabaseテーブル作成スクリプト
├── routers/
│   ├── auth.py          # ログイン/ログアウト
│   ├── expenses.py      # 支出API（一覧/追加/削除）
│   └── csv_import.py    # PayPay CSVインポート
├── static/
│   └── index.html       # メイン画面（レスポンシブ対応）
├── templates/
│   └── login.html       # ログインページ
├── api/
│   └── index.py         # Vercel用エントリーポイント
├── data/                # JSONデータ（ローカル開発用・gitignore対象）
├── .env                 # 環境変数（gitignore対象）
├── .gitignore
├── vercel.json          # Vercelデプロイ設定
├── requirements.txt
└── README.md
```

## ローカル起動手順

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env` に以下を設定（Supabase未設定の場合はローカルJSONで動作）：

```
SECRET_KEY=（ランダムな文字列）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=（任意のパスワード）
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=（anonキー）
```

### 3. サーバー起動

```bash
python main.py
```

### 4. ブラウザでアクセス

```
http://localhost:8000
```

## 機能

- **ログイン認証**：Flask-Login によるセッション認証（未ログイン時は `/login` へ自動リダイレクト）
- **3タブ構成（ボトムナビ）**：ホーム / 月別 / 年間
  - **ホーム**：常設の即入力フォーム＋よく使う支出のワンタップ・ショートカット＋未分類To-Do通知＋直近タイムライン
  - **月別**：月切替・合計・カテゴリ別・円グラフ・日別折れ線・並び替え付き一覧
  - **年間**：年切替・年間合計・月別折れ線・年間円グラフ・月別内訳表
- **動的FAB**：月別/年間は常時表示、ホームは入力フォームが隠れた時だけ表示。タップで入力ボトムシートを前面表示
- **支出の追加・編集・削除**：編集はモーダルから（PATCH）
- **並び替え**：日付（新旧）・金額（高安）・カテゴリ順（フロントエンド）
- **グラフ**：Chart.js（円グラフ＝割合・ホバーで金額%／折れ線＝日別・月別推移）
- **カテゴリのカスタマイズ**：Supabaseの `categories` テーブルで管理。追加・名称/絵文字/色の編集・削除が可能（管理モーダル）
- **ショートカット**：`shortcuts` テーブルでよく使う支出を登録。ワンタップで即記録（金額未設定なら入力モーダル）
- **予算管理**：`budgets` テーブルで月の合計予算・カテゴリ別予算を設定（upsert）。ホーム最上部の通知エリアに予算超過（赤）／残りわずか（黄・しきい値%）／残り予算（常時表示・任意）を表示。予算詳細セクションにカテゴリ別プログレスバー（超過は赤）
- **通知設定**：残り予算の常時表示ON/OFF、通知しきい値（20/10/5%）を `settings` テーブルに保存
- **パスワード変更**：設定モーダルから変更。bcryptでハッシュ化して `settings` テーブルに保存（`.env` の `ADMIN_PASSWORD` はハッシュ未設定時のフォールバック）
- **未分類の整理**：CSV取込でカテゴリ不明な支出を「未分類」とし、通知エリアからまとめてカテゴリ設定
- **PayPay CSVインポート**：新形式（取引日・出金金額（円）・取引先・取引内容…）と旧形式の両対応。重複・チャージ・返金は自動スキップ、カテゴリ自動推定
- **レスポンシブ対応**：スマホ（375px）最適化

## データ層について（拡張のしやすさ）

`db.py` は **JSONファイル** と **Supabase** を自動で切り替えます：

- `.env` に `SUPABASE_URL` / `SUPABASE_ANON_KEY` があれば → **Supabase**
- なければ → **ローカルJSONファイル**（`data/expenses.json`）

APIルーター（`routers/expenses.py`）は `db.py` の関数を呼ぶだけなので、
**保存先を変えてもフロントエンド・APIには一切影響しません**。

## Supabaseセットアップ

### テーブル作成

`.env` に `SUPABASE_DB_URL`（DB直接接続URL）を設定して実行：

```bash
python setup_db.py
```

または Supabase ダッシュボードの SQL Editor で `supabase_setup.sql` を実行。

## デプロイ（Vercel）

```bash
vercel --prod
```

環境変数（`SECRET_KEY` / `ADMIN_USERNAME` / `ADMIN_PASSWORD` /
`SUPABASE_URL` / `SUPABASE_ANON_KEY`）は Vercel のプロジェクト設定に登録します。

## 今後の拡張計画

### フェーズ3：Gmail連携（PayPay決済メール自動取込）
- Gmail APIでPayPayの決済通知メールを取得
- メール本文から金額・店舗名を抽出
- `db.add_expense()` を呼ぶだけで取り込み完了

### フェーズ4：その他機能追加
- 複数ユーザー対応（Supabase Auth + RLS）
- 月次レポート出力（PDF/CSV）
- 予算設定・超過アラート
- グラフ表示（Chart.js）
