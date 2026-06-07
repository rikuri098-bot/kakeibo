"""
Vercel用エントリーポイント
Vercelはこのファイルの `app` オブジェクトをWSGIアプリとして使う
"""
import sys, os
# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # FlaskアプリをインポートするだけでOK

# Vercelはこの `app` を自動でWSGIとして認識する
