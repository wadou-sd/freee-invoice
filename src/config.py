"""設定の読み込み（.env と環境変数）。外部ライブラリ不要。"""
import os


def _load_dotenv(path):
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_load_dotenv(os.path.join(_BASE, ".env"))


def _req(key):
    v = os.environ.get(key)
    if not v:
        raise SystemExit(f"環境変数 {key} が未設定です（.env を確認してください）")
    return v


FREEE_CLIENT_ID = _req("FREEE_CLIENT_ID")
FREEE_CLIENT_SECRET = _req("FREEE_CLIENT_SECRET")
FREEE_COMPANY_ID = _req("FREEE_COMPANY_ID")
SUPABASE_URL = _req("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_KEY = _req("SUPABASE_SERVICE_KEY")
BILLING_START_DATE = os.environ.get("BILLING_START_DATE", "2025-08-01")

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
FREEE_API_BASE = "https://api.freee.co.jp/iv"
FREEE_TOKEN_URL = "https://accounts.secure.freee.co.jp/public_api/token"
