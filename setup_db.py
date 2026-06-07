"""
Supabaseテーブル自動作成スクリプト
.envに SUPABASE_DB_URL を設定してから実行：
  python setup_db.py

SUPABASE_DB_URL は Supabase Dashboard → Settings → Database
→ Connection string → Python 形式でコピーできる
（例）postgresql://postgres.xxxx:PASSWORD@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
"""
import os, sys
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL", "")

if not DB_URL:
    print("❌ .env に SUPABASE_DB_URL が設定されていません")
    print()
    print("Supabase Dashboard → Settings → Database → Connection string")
    print("→ Python 形式をコピーして .env に追加してください:")
    print("  SUPABASE_DB_URL=postgresql://postgres.xxxx:PASSWORD@...")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("psycopg2をインストールします...")
    os.system("py -3.14 -m pip install psycopg2-binary")
    import psycopg2

SQL = """
CREATE TABLE IF NOT EXISTS expenses (
    id             TEXT        PRIMARY KEY,
    date           DATE        NOT NULL,
    amount         INTEGER     NOT NULL CHECK (amount > 0),
    category       TEXT        NOT NULL,
    payment_method TEXT        NOT NULL,
    memo           TEXT        DEFAULT '',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses (date DESC);

ALTER TABLE expenses DISABLE ROW LEVEL SECURITY;
"""

print("Supabaseに接続中...")
try:
    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(SQL)
    cur.execute("SELECT COUNT(*) FROM expenses")
    count = cur.fetchone()[0]
    print(f"✅ テーブル作成完了！現在の件数: {count}")
    conn.close()
except Exception as e:
    print(f"❌ エラー: {e}")
    sys.exit(1)
