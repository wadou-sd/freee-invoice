"""freee 初回認可（トークンをSQLiteに保存する）。

使い方:
  1) python3 scripts/authorize.py          # 認可URLを表示
  2) 表示URLをブラウザで開き、freeeでログイン・許可
  3) 画面に出た「認可コード」をコピー
  4) python3 scripts/authorize.py <認可コード>   # トークンを取得・保存
"""
import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import config, store  # noqa: E402

AUTH_URL = "https://accounts.secure.freee.co.jp/public_api/authorize"


def build_url():
    q = urllib.parse.urlencode({
        "client_id": config.FREEE_CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "response_type": "code",
    })
    return f"{AUTH_URL}?{q}"


def exchange(code):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": config.FREEE_CLIENT_ID,
        "client_secret": config.FREEE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        config.FREEE_TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"トークン取得失敗: {e.code} {e.read().decode()}")


def main():
    args = sys.argv[1:]
    if not args:
        print("■ 次のURLをブラウザで開き、freeeでログイン・許可してください:\n")
        print(build_url())
        print("\n■ 表示された認可コードを使って、もう一度実行してください:")
        print("   python3 scripts/authorize.py <認可コード>")
        return
    code = args[0].strip()
    tok = exchange(code)
    now = datetime.now(timezone.utc)
    exp = (now + timedelta(seconds=int(tok.get("expires_in", 21600)))).isoformat()
    store.insert_token(
        tok["access_token"], tok["refresh_token"], exp,
        company_id=str(config.FREEE_COMPANY_ID))
    print("✅ トークンを保存しました。")
    print("   有効期限:", exp)
    print("   確認: python3 scripts/check_token.py")


if __name__ == "__main__":
    main()
