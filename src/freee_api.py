"""freee請求書API(iv)の薄いラッパー。外部ライブラリ不要(urllib)。"""
import calendar
import json
import urllib.request
import urllib.parse
import urllib.error

from . import config


def _get(path, token, params=None):
    url = config.FREEE_API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def list_delivery_slips(token, period_ym):
    """指定月(YYYY-MM)の納品書を全件取得。"""
    y, m = map(int, period_ym.split("-"))
    last = calendar.monthrange(y, m)[1]
    out, off = [], 0
    while True:
        d = _get("/delivery_slips", token, {
            "company_id": config.FREEE_COMPANY_ID,
            "start_delivery_slip_date": f"{y:04d}-{m:02d}-01",
            "end_delivery_slip_date": f"{y:04d}-{m:02d}-{last:02d}",
            "limit": 100, "offset": off,
        }).get("delivery_slips", [])
        if not d:
            break
        out += d
        if len(d) < 100:
            break
        off += 100
    return out


def get_delivery_slip(token, slip_id):
    return _get(f"/delivery_slips/{slip_id}", token,
                {"company_id": config.FREEE_COMPANY_ID})["delivery_slip"]


def list_all_invoices(token):
    out, off = [], 0
    while True:
        d = _get("/invoices", token, {
            "company_id": config.FREEE_COMPANY_ID, "limit": 100, "offset": off,
        }).get("invoices", [])
        if not d:
            break
        out += d
        if len(d) < 100:
            break
        off += 100
    return out


def create_invoice(token, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        config.FREEE_API_BASE + "/invoices", data=data, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"請求書作成失敗: {e.code} {e.read().decode()}")
