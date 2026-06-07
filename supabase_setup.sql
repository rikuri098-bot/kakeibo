-- ============================================================
-- Supabase テーブル作成スクリプト
-- Supabase の SQL Editor で実行してください
-- ============================================================

-- expenses テーブル
CREATE TABLE IF NOT EXISTS expenses (
    id             TEXT        PRIMARY KEY,
    date           DATE        NOT NULL,
    amount         INTEGER     NOT NULL CHECK (amount > 0),
    category       TEXT        NOT NULL,
    payment_method TEXT        NOT NULL,
    memo           TEXT        DEFAULT '',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- 日付降順インデックス（一覧取得を高速化）
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses (date DESC);

-- RLS（Row Level Security）は今回無効化（管理者のみ使用するため）
-- 本番で複数ユーザー対応する場合は有効にすること
ALTER TABLE expenses DISABLE ROW LEVEL SECURITY;

-- 確認クエリ
SELECT COUNT(*) FROM expenses;
