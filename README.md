# 家計簿アプリ

ローカルで動くシンプルな家計簿Webアプリです。

## フォルダ構成

```
kakeibo/
├── main.py              # FastAPIエントリーポイント・起動ファイル
├── models.py            # データモデル定義（Pydantic）
├── db.py                # データ永続化レイヤー（JSON操作）
├── routers/
│   └── expenses.py      # 支出APIルーター
├── static/
│   └── index.html       # フロントエンド（HTML/Tailwind/JS）
├── data/                # JSONデータ保存先（gitignore対象）
│   └── expenses.json    # 支出データ（自動生成）
├── .env                 # 環境変数（gitignore対象）
├── .gitignore
├── requirements.txt
└── README.md
```

## 起動手順

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. サーバー起動

```bash
python main.py
```

### 3. ブラウザでアクセス

```
http://localhost:8000
```

## 機能

- **支出入力**：日付・金額・カテゴリ・支払い方法・メモを入力して追加
- **一覧表示**：入力済み支出を新しい順に表示
- **サマリー**：当月の合計金額・カテゴリ別合計を表示
- **削除**：各支出の削除ボタンで個別削除

## 今後の拡張計画

### フェーズ2：Gmail連携（PayPay決済メール自動取込）
- Gmail APIでPayPayの決済通知メールを取得
- メール本文から金額・店舗名を正規表現で抽出
- `db.py` に `add_expense()` を呼び出すだけで取り込み完了

### フェーズ3：Supabase移行
- `db.py` の関数シグネチャを変えずにSupabaseクライアントに差し替え
- `.env` に `SUPABASE_URL` と `SUPABASE_KEY` を追加するだけ

### フェーズ4：その他機能追加
- 月次レポート出力（PDF/CSV）
- 予算設定・超過アラート
- グラフ表示（Chart.js）
