"""動作確認: 有効なアクセストークンを取得し、iv APIの疎通を確認する。

実行: python3 scripts/check_token.py
"""
import os
import sys
import json
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import freee_token, config  # noqa: E402


def main():
    at = freee_token.get_valid_access_token()
    print("アクセストークン取得OK（先頭8文字）:", at[:8], "...")
    req = urllib.request.Request(
        f"{config.FREEE_API_BASE}/invoices/templates?company_id={config.FREEE_COMPANY_ID}",
        headers={"Authorization": f"Bearer {at}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    print("iv API 疎通OK。請求書テンプレート:",
          [t.get("name") for t in d.get("templates", [])])


if __name__ == "__main__":
    main()
