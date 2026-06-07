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
- **支出入力**：日付・金額・カテゴリ・支払い方法・メモを入力して追加
- **一覧表示**：入力済み支出を新しい順に表示
- **サマリー**：当月の合計金額・カテゴリ別合計（プログレスバー付き）
- **削除**：各支出の個別削除
- **PayPay CSVインポート**：取引履歴CSVを一括取込（重複・チャージは自動スキップ）
- **レスポンシブ対応**：スマホ（375px）・タブレット（768px）・PC（1024px）

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
