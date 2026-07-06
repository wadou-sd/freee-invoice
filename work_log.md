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

✅ 2026-07-03 Supabase初期スキーマの適用（0001_init）
- partners / billing_runs / invoice_links / issue_jobs / freee_tokens を作成（ユーザー承認済み）
- 二重請求防止: invoice_links.freee_delivery_slip_id と issue_jobs.idempotency_key にUNIQUE
- 全テーブルRLS有効。SQLを supabase/migrations/0001_init.sql にコミット

✅ 2026-07-06 開発ロードマップ作成（docs/development-roadmap.md）
- Phase 0〜7 に分割。進め方: 費用ゼロ／小さく確認／安全側

✅ 2026-07-06 Phase 2 freee OAuth連携 完了
- アプリ権限「[freee請求書] 全帳票種別」参照＋更新を付与し再認可 → invoice:docs:write 取得
- iv API 疎通OK。company_id=1506256。トークンを freee_tokens に保存

✅ 2026-07-06 取引先の名寄せ確定・対象開始・ドライラン検証（docs/partner-aliases.md）
- 名寄せ6組を統合、平沼・西川・県立2校は分離。対象開始=2026-07-01（過去分は対象外）
- ドライラン(2026-06,読み取り): 納品書6件→請求書3通。秩鉄商事3枚→1通(53,676円/5明細)を確認

✅ 2026-07-06 Phase 4 テスト: APIで下書き請求書を実作成
- 秩鉄商事の2026-06分（納品書3枚合算）を POST /invoices で下書き作成
- 結果: invoice_id=62472147 / INV-0000000952 / 御中 / 53,676円 / 5明細 / 税別(out)
- 納品書の税区分・端数設定を引き継ぐことで金額一致を確認
- ※過去月のテストのため、確認後に田口さんが取消/削除する予定
