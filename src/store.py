"""Supabase(PostgREST)への薄いアクセス層。外部ライブラリ不要(urllib)。

RLS有効・ポリシー無しのため、service_role(secret) キーで接続し RLS をバイパスする。
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


def _is_conflict(err):
    s = str(err)
    return "409" in s or "23505" in s or "duplicate key" in s


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


# --- billing_runs ---

def get_or_create_billing_run(period_ym):
    rows = _request("GET", "billing_runs",
                    params={"select": "*", "period_ym": f"eq.{period_ym}", "limit": 1})
    if rows:
        return rows[0]
    created = _request("POST", "billing_runs",
                       body={"period_ym": period_ym, "status": "running"},
                       prefer="return=representation")
    return created[0]


def update_billing_run(run_id, status):
    _request("PATCH", "billing_runs",
             params={"id": f"eq.{run_id}"},
             body={"status": status, "finished_at": _now_iso()},
             prefer="return=minimal")


# --- invoice_links / issue_jobs ---

def get_billed_slip_ids():
    rows = _request("GET", "invoice_links", params={"select": "freee_delivery_slip_id"})
    return {r["freee_delivery_slip_id"] for r in (rows or [])}


def insert_invoice_link(run_id, freee_invoice_id, freee_delivery_slip_id, period_ym):
    try:
        _request("POST", "invoice_links",
                 body={"billing_run_id": run_id,
                       "freee_invoice_id": freee_invoice_id,
                       "freee_delivery_slip_id": freee_delivery_slip_id,
                       "period_ym": period_ym},
                 prefer="return=minimal")
    except RuntimeError as e:
        if _is_conflict(e):
            return  # 既に紐付け済み（二重防止）
        raise


def record_issue_job(run_id, rep_pid, period_ym, status, freee_response=None, error=None):
    key = f"{period_ym}:{rep_pid}"
    body = {"billing_run_id": run_id, "status": status, "idempotency_key": key}
    if freee_response is not None:
        body["freee_response"] = freee_response
    if error is not None:
        body["error"] = error
    try:
        _request("POST", "issue_jobs", body=body, prefer="return=minimal")
    except RuntimeError as e:
        if not _is_conflict(e):
            raise
        upd = {"status": status, "updated_at": _now_iso()}
        if freee_response is not None:
            upd["freee_response"] = freee_response
        if error is not None:
            upd["error"] = error
        _request("PATCH", "issue_jobs",
                 params={"idempotency_key": f"eq.{key}"},
                 body=upd, prefer="return=minimal")
