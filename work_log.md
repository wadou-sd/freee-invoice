# 作業ログ（work_log.md）

このファイルは、開発の各作業を記録するログです。
- 作業前に 🔄（開始）を記録
- 作業完了後に ✅（完了）を記録

---

✅ 2026-07-02 開発環境セットアップ完了
- PCツール・GitHub / Supabase / Geminiキー・MCP接続・Xserver VPS(162.43.32.67)を整備

✅ 2026-07-03 システム設計（docs/system-design.md）
- 納品書を正／月末締めで取引先ごとに集計／下書きまで自動＋発行・送付は手動（方式B）

✅ 2026-07-03 合算方式検証：APIに合算なし。GET /delivery_slips → 明細集計 → POST /invoices で確定

✅ 2026-07-03 Supabase初期スキーマ（0001_init）partners/billing_runs/invoice_links/issue_jobs/freee_tokens。全RLS有効

✅ 2026-07-06 開発ロードマップ（docs/development-roadmap.md）Phase 0〜7

✅ 2026-07-06 Phase 2 freee OAuth：[freee請求書]全帳票種別 参照＋更新で invoice:docs:write 取得。company_id=1506256

✅ 2026-07-06 取引先名寄せ・対象開始（docs/partner-aliases.md）名寄せ6組統合、対象開始=2025-08-01

✅ 2026-07-06 Phase 4 テスト：秩鉄商事2026-06を POST /invoices で下書き作成 INV-0000000952 / 53,676円（確認後取消予定）

✅ 2026-07-06 当期の未請求チェック：上林・大井常明・福島陽子 の3件のみ（他は請求済み、田口さんの確認でそのまま）

✅ 2026-07-06 Phase 5 トークン自動更新 完成・動作確認
- VPSをmainへ同期。.env作成(chmod600)。依存ゼロで config/store(Supabase REST)/freee_token 実装
- リフレッシュ＋Supabase書戻し検証 OK

✅ 2026-07-06 Phase 5 締めバッチ本体 実装・ドライラン検証
- src/aliases.py(名寄せ pid→代表), freee_api.py(iv), billing.py(本体), scripts/run_billing.py 追加
- 二重防止2段: ①invoice_links既出の納品書除外 ②freee上で代表取引先×当月の請求書があれば除外
- ドライラン 2026-03: 納品書13→取引先8、既存2件skip、作成予定6通（佐野さんは名寄せで5枚→1通）を確認。POSTなし
- 次: 月末cron設定（承認後）。初回本番は7月末（現時点7月は納品0件）
