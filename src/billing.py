"""締めバッチ本体。

流れ: 対象月の納品書取得 → 名寄せ → 取引先ごとに明細を合算 → 下書き作成
→ invoice_links / issue_jobs に記録。
二重作成防止:
  (1) invoice_links にある納品書は除外（バッチが請求済みの分を確実に除外）。
  (2) freee に「代表取引先 × 当月(billing_date)」の請求書があれば、警告ログを
      出しつつ下書きは作成する。前月分を当月付で発行するケースでの誤スキップ
      （＝請求漏れ）を防ぐため。重複したときは下書き確認の段階で気づける。
作成は常に下書き（発行・送付は人の手で）。
"""
import calendar

from . import config, freee_token, freee_api, store, aliases

DEFAULT_TEMPLATE_ID = 1961370  # 窓付き
_LINE_KEYS = ("type", "description", "quantity", "unit", "unit_price",
              "tax_rate", "reduced_tax_rate")


def _last_day(y, m):
    return calendar.monthrange(y, m)[1]


def _build_lines(details):
    lines = []
    for d in details:
        for ln in d.get("lines", []):
            lines.append({k: ln[k] for k in _LINE_KEYS if ln.get(k) is not None})
    return lines


def run(period_ym, dry_run=False, template_id=DEFAULT_TEMPLATE_ID, log=print):
    y, m = map(int, period_ym.split("-"))
    token = freee_token.get_valid_access_token()

    slips = freee_api.list_delivery_slips(token, period_ym)
    slips = [s for s in slips if s["delivery_slip_date"] >= config.BILLING_START_DATE]
    billed = store.get_billed_slip_ids()
    slips = [s for s in slips if str(s["id"]) not in billed]

    # freee上で「代表取引先 × 当月(billing_date)」の請求書がある組（重複の可能性）
    existing = set()
    for iv in freee_api.list_all_invoices(token):
        bd = iv.get("billing_date") or ""
        existing.add((aliases.representative_pid(iv.get("partner_id")), bd[:7]))

    groups = {}
    for s in slips:
        rep = aliases.representative_pid(s["partner_id"])
        groups.setdefault(rep, []).append(s)

    log(f"[{period_ym}] 対象納品書 {len(slips)}件 / 取引先(名寄せ後) {len(groups)}")

    # (rep, slips, warn) の形で計画を作る。warn=当月請求書が既にある（要確認）
    plan = []
    for rep, g in groups.items():
        warn = (rep, period_ym) in existing
        if warn:
            log(f"  ⚠ pid={rep} は当月(billing_date)の請求書が既に存在。念のため下書きは作成（要確認）")
        plan.append((rep, g, warn))

    if dry_run:
        for rep, g, warn in plan:
            tot = sum(x["total_amount"] for x in g)
            mark = "⚠要確認 " if warn else ""
            log(f"  [DRY] {mark}pid={rep} '{g[0]['partner_name']}' 納品書{len(g)}件 → 請求書1通 / {tot:,}円")
        log(f"[{period_ym}] DRY-RUN: 作成予定 {len(plan)}通（作成はしません）")
        return

    run_row = store.get_or_create_billing_run(period_ym)
    ok, ng = 0, 0
    for rep, g, warn in plan:
        try:
            details = [freee_api.get_delivery_slip(token, s["id"]) for s in g]
            h = details[0]
            body = {
                "company_id": int(config.FREEE_COMPANY_ID),
                "template_id": template_id,
                "partner_id": int(rep),
                "billing_date": f"{y:04d}-{m:02d}-{_last_day(y, m):02d}",
                "subject": f"{y}年{m}月ご請求分",
                "tax_entry_method": h["tax_entry_method"],
                "tax_fraction": h["tax_fraction"],
                "withholding_tax_entry_method": h["withholding_tax_entry_method"],
                "partner_title": h.get("partner_title") or "御中",
                "lines": _build_lines(details),
            }
            inv = freee_api.create_invoice(token, body)["invoice"]
            store.record_issue_job(run_row["id"], rep, period_ym, "drafted", freee_response=inv)
            for s in g:
                store.insert_invoice_link(run_row["id"], str(inv["id"]), str(s["id"]), period_ym)
            ok += 1
            mark = "⚠要確認 " if warn else ""
            log(f"  OK: {mark}{inv.get('invoice_number')} pid={rep} "
                f"{inv.get('total_amount'):,}円 ({len(g)}枚合算)")
        except Exception as e:  # noqa: BLE001
            ng += 1
            try:
                store.record_issue_job(run_row["id"], rep, period_ym, "failed", error=str(e))
            except Exception:  # noqa: BLE001
                pass
            log(f"  NG: pid={rep} 失敗: {e}")
    warns = sum(1 for _, _, w in plan if w)
    store.update_billing_run(run_row["id"], "drafted" if ng == 0 else "failed")
    log(f"[{period_ym}] 完了: 成功 {ok} / 失敗 {ng} / 要確認 {warns}")
