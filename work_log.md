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
- 設計合意事項: 納品書を正／月末締めで取引先ごとに合算／下書きまで自動＋確認・発行・送付は手動（方式B）
- freee請求書API利用（会計APIのPOSTは廃止済み）。合算のAPI可否は実装着手時に要確認
