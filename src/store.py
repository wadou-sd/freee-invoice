"""ローカルSQLiteへのアクセス層（Supabase依存を排除）。

freee-invoice の状態（トークン・実行履歴・請求書リンク・発行ジョブ）を
VPS内のSQLiteファイルに保存する。外部DBに依存しないため、休止や
名前解決失敗で月末バッチが止まることがない。

既存の store.py（Supabase版）と同じ関数シグネチャ・戻り値を保つため、
billing.py / freee_token.py は一切変更不要。
"""
import os
import sqlite3
import json
import uuid
from datetime import datetime, timezone

from . import config

_DB_PATH = os.environ.get(
    "SQLITE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "billing.db"),
)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _conn():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    c = sqlite3.connect(_DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS freee_tokens (
              id TEXT PRIMARY KEY,
              access_token TEXT NOT NULL,
              refresh_token TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              company_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS billing_runs (
              id TEXT PRIMARY KEY,
              period_ym TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL DEFAULT 'running',
              started_at TEXT NOT NULL,
              finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS invoice_links (
              id TEXT PRIMARY KEY,
              billing_run_id TEXT,
              freee_invoice_id TEXT,
              freee_delivery_slip_id TEXT NOT NULL UNIQUE,
              period_ym TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS issue_jobs (
              id TEXT PRIMARY KEY,
              billing_run_id TEXT,
              status TEXT NOT NULL DEFAULT 'pending',
              idempotency_key TEXT NOT NULL UNIQUE,
              freee_response TEXT,
              error TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_issue_jobs_run ON issue_jobs(billing_run_id);
            """
        )


_init()


# --- freee_tokens ---

def get_latest_token():
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM freee_tokens ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def update_token(token_id, access_token, refresh_token, expires_at):
    with _conn() as c:
        c.execute(
            "UPDATE freee_tokens SET access_token=?, refresh_token=?, expires_at=?, updated_at=? WHERE id=?",
            (access_token, refresh_token, expires_at, _now_iso(), token_id),
        )


def insert_token(access_token, refresh_token, expires_at, company_id=None):
    """初回認可でトークンを新規保存する（Supabase版には無かった補助関数）。"""
    now = _now_iso()
    with _conn() as c:
        c.execute(
            "INSERT INTO freee_tokens (id, access_token, refresh_token, expires_at, company_id, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), access_token, refresh_token, expires_at, company_id, now, now),
        )


# --- billing_runs ---

def get_or_create_billing_run(period_ym):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM billing_runs WHERE period_ym=? LIMIT 1", (period_ym,)
        ).fetchone()
        if row:
            return dict(row)
        rid = str(uuid.uuid4())
        c.execute(
            "INSERT INTO billing_runs (id, period_ym, status, started_at) VALUES (?,?,?,?)",
            (rid, period_ym, "running", _now_iso()),
        )
        row = c.execute("SELECT * FROM billing_runs WHERE id=?", (rid,)).fetchone()
        return dict(row)


def update_billing_run(run_id, status):
    with _conn() as c:
        c.execute(
            "UPDATE billing_runs SET status=?, finished_at=? WHERE id=?",
            (status, _now_iso(), run_id),
        )


# --- invoice_links ---

def get_billed_slip_ids():
    with _conn() as c:
        rows = c.execute(
            "SELECT freee_delivery_slip_id FROM invoice_links"
        ).fetchall()
        return {r["freee_delivery_slip_id"] for r in rows}


def insert_invoice_link(run_id, freee_invoice_id, freee_delivery_slip_id, period_ym):
    with _conn() as c:
        try:
            c.execute(
                "INSERT INTO invoice_links (id, billing_run_id, freee_invoice_id, freee_delivery_slip_id, period_ym, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), run_id, freee_invoice_id, freee_delivery_slip_id, period_ym, _now_iso()),
            )
        except sqlite3.IntegrityError:
            return  # 既に紐付け済み（二重防止）


# --- issue_jobs ---

def record_issue_job(run_id, rep_pid, period_ym, status, freee_response=None, error=None):
    key = f"{period_ym}:{rep_pid}"
    resp = json.dumps(freee_response, ensure_ascii=False) if freee_response is not None else None
    now = _now_iso()
    with _conn() as c:
        exists = c.execute(
            "SELECT id FROM issue_jobs WHERE idempotency_key=?", (key,)
        ).fetchone()
        if exists:
            sets, vals = ["status=?", "updated_at=?"], [status, now]
            if resp is not None:
                sets.append("freee_response=?"); vals.append(resp)
            if error is not None:
                sets.append("error=?"); vals.append(error)
            vals.append(key)
            c.execute(f"UPDATE issue_jobs SET {', '.join(sets)} WHERE idempotency_key=?", vals)
        else:
            c.execute(
                "INSERT INTO issue_jobs (id, billing_run_id, status, idempotency_key, freee_response, error, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), run_id, status, key, resp, error, now, now),
            )
