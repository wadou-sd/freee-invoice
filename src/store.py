"""Supabase(PostgREST)への薄いアクセス層。外部ライブラリ不要(urllib)。

RLS有効・ポリシー無しのため、service_role キーで接続する（RLSをバイパス）。
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

from . import config


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _request(method, path, params=None, body=None, prefer=None):
    url = f"{config.SUPABASE_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
            return json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Supabase {method} {path} 失敗: {e.code} {e.read().decode()}")


# --- freee_tokens ---

def get_latest_token():
    rows = _request("GET", "freee_tokens",
                    params={"select": "*", "order": "created_at.desc", "limit": 1})
    return rows[0] if rows else None


def update_token(token_id, access_token, refresh_token, expires_at):
    _request("PATCH", "freee_tokens",
             params={"id": f"eq.{token_id}"},
             body={"access_token": access_token,
                   "refresh_token": refresh_token,
                   "expires_at": expires_at,
                   "updated_at": _now_iso()},
             prefer="return=minimal")
