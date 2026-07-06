"""freeeアクセストークンの取得・自動更新。

- freee_tokens から最新トークンを読む
- 期限が近ければ refresh_token で更新し、新しいトークンを保存する
  （リフレッシュトークンは使うたびに新しくなるため必ず保存する）
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

from . import config, store

_REFRESH_BUFFER = timedelta(minutes=10)


def _refresh(refresh_token):
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": config.FREEE_CLIENT_ID,
        "client_secret": config.FREEE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "redirect_uri": config.REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        config.FREEE_TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"トークン更新失敗: {e.code} {e.read().decode()}")


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def get_valid_access_token():
    row = store.get_latest_token()
    if not row:
        raise SystemExit("freee_tokens にトークンがありません。初回認可を実施してください。")
    now = datetime.now(timezone.utc)
    if _parse(row["expires_at"]) - now > _REFRESH_BUFFER:
        return row["access_token"]
    tok = _refresh(row["refresh_token"])
    new_exp = (now + timedelta(seconds=int(tok.get("expires_in", 21600)))).isoformat()
    store.update_token(row["id"], tok["access_token"], tok["refresh_token"], new_exp)
    return tok["access_token"]
