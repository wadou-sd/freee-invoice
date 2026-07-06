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
- 全体像・データ設計・処理フロー・freee API利用方針・状態遷移・将来拡張の初版
- 設計合意: 納品書を正／月末締めで取引先ごとに集計／下書きまで自動＋確認・発行・送付は手動（方式B）

✅ 2026-07-03 合算方式のAPI可否を検証（費用ゼロ）
- freee請求書API OpenAPI原本を確認。APIに合算機能はなし。POST /invoices は明細(lines)を直接渡す方式のみ
- 方針: GET /delivery_slips → 明細集計 → POST /invoices

✅ 2026-07-03 Supabase初期スキーマ適用（0001_init）
- partners / billing_runs / invoice_links / issue_jobs / freee_tokens を作成
- 二重請求防止: invoice_links.freee_delivery_slip_id / issue_jobs.idempotency_key にUNIQUE。全テーブルRLS有効

✅ 2026-07-06 開発ロードマップ作成（docs/development-roadmap.md）Phase 0〜7

✅ 2026-07-06 Phase 2 freee OAuth連携 完了
- アプリ権限「[freee請求書] 全帳票種別」参照＋更新 → invoice:docs:write 取得。company_id=1506256

✅ 2026-07-06 取引先名寄せ確定・対象開始（docs/partner-aliases.md）
- 名寄せ6組統合、平沼・西川・県立2校は分離。対象開始=2025-08-01（当期）
- ドライラン(2026-06): 納品書6件→請求書3通。秩鉄商事3枚→1通(53,676円)確認

✅ 2026-07-06 Phase 4 テスト: APIで下書き請求書を実作成
- 秩鉄商事2026-06分を POST /invoices で下書き作成 → INV-0000000952 / 53,676円 / 5明細（確認後取消予定）

✅ 2026-07-06 当期の請求状況チェック（partner_id基準）
- 当期(2025-08〜)の未請求は 上林・大井常明・福島陽子 の3件のみ（他は請求済み）

✅ 2026-07-06 Phase 5 トークン自動更新モジュール 完成・動作確認
- VPSをmainへ同期。.env作成（chmod600、Git非管理）
- 依存ゼロ(標準ライブラリ)で src/config・store(Supabase REST)・freee_token・scripts/check_token を実装
- check_token.py: アクセストークン取得＋iv API疎通OK（テンプレート: 窓付き/窓付き封筒）
- リフレッシュ＋Supabase書き戻し検証 OK（AT更新・expires_at更新確認、scopeにinvoice:docs:write）
- 締め=月末、通知=ログ。次: 締めバッチ本体（対象抽出→名寄せ→集約→下書き→記録）
