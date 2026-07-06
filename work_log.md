# 作業ログ（work_log.md）

このファイルは、開発の各作業を記録するログです。
- 作業前に 🔄（開始）を記録
- 作業完了後に ✅（完了）を記録

---

✅ 2026-07-02 開発環境セットアップ完了
- PCツール（Node.js / Python / SSHパッケージ）導入
- GitHub / Supabase / Gemini API キー取得
- MCP接続（github / supabase / ssh）確立
- Xserver VPS 契約・SSH接続確認（162.43.32.67）
- VPSに /root/projects/freee-invoice を作成し GitHub と連携

✅ 2026-07-03 システム設計ドキュメント作成（docs/system-design.md）
- 全体像・データ設計・処理フロー・freee API利用方針・状態遷移・将来拡張の初版を作成
- 設計合意事項: 納品書を正／月末締めで取引先ごとに集計／下書きまで自動＋確認・発行・送付は手動（方式B）
- freee請求書API利用（会計APIのPOSTは廃止済み）

✅ 2026-07-03 合算方式のAPI可否を検証（費用ゼロ）
- freee請求書API OpenAPI原本（freee/freee-api-schema iv/open-api-3）を確認
- 結論: APIに納品書合算機能はなし。POST /invoices は明細(lines)を直接渡す方式のみ
- 方針: GET /delivery_slips で取得→明細集計→POST /invoices（当初案②）で確定
- 設計書 §3・§10 に反映済み

✅ 2026-07-03 Supabase初期スキーマの適用（0001_init）
- partners / billing_runs / invoice_links / issue_jobs / freee_tokens を作成（ユーザー承認済み）
- 二重請求防止: invoice_links.freee_delivery_slip_id と issue_jobs.idempotency_key にUNIQUE
- 全テーブルRLS有効（ポリシーなし＝バックエンド専用）
- SQLを supabase/migrations/0001_init.sql にコミット。list_tablesで5テーブル作成を確認

✅ 2026-07-06 開発ロードマップ作成（docs/development-roadmap.md）
- Phase 0〜7 に分割。Phase 0-1 完了、次は Phase 2（freee OAuth連携）
- 進め方の原則: 費用ゼロ／小さく確認しながら／安全側（下書きまで自動・発行送付は手動）

✅ 2026-07-06 Phase 2 freee OAuth連携 完了
- freeeアプリ作成（和銅農園 請求書自動作成 / Client ID: 759738689736560 / コールバックURL: oob）
- 権限のハマりどころ: 会計の帳票権限は参照のみ（会計API帳票POST廃止の名残）
- 解決: アプリ権限「[freee請求書] 全帳票種別」の参照＋更新を付与し再認可
- 取得スコープ: accounting:companies:read accounting:docs:read invoice:docs:read invoice:docs:write
- iv API 疎通OK: 請求書テンプレート(1961370窓付き/1897124窓付き封筒)・納品書一覧を取得確認
- company_id=1506256（株式会社 和銅農園）。トークンを freee_tokens に保存
- roadmap の Phase 2 を完了に更新。次は Phase 3（納品書取得と明細集計）
