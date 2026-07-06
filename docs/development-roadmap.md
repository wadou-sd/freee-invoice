# freee-invoice 開発ロードマップ

最終更新: 2026-07-06

関連ドキュメント: [system-design.md](./system-design.md) / [partner-aliases.md](./partner-aliases.md)

## 進め方の原則

- **費用をかけない** … 既存VPS（162.43.32.67）＋ Supabase無料枠 ＋ freee で完結。
- **小さく確認しながら** … 各フェーズは「動く最小」を作り、田口が確認してから次へ。
- **安全側で** … Supabase/VPS書き込みは事前承認。請求書は下書きまで。発行・送付は田口が手動（方式B）。

## 進捗サマリ

| Phase | 内容 | 状態 |
|-------|------|------|
| 0 | 環境構築 | ✅ 完了 |
| 1 | 設計（全体像・データ設計・API方針・DBスキーマ） | ✅ 完了 |
| 2 | freee OAuth連携（トークン取得・保存・更新） | ✅ 完了 |
| 3 | 納品書の取得と明細集計 | ✅ 完了 |
| 4 | 請求書の下書き作成と記録 | ✅ 完了 |
| 5 | 月次締めバッチの統合（cron） | ✅ 完了 |
| 6 | 運用開始・検証 | ⬜ 進行中（初回本番=7月末） |
| 7 | 将来拡張 | ⬜ 保留 |

**MVP完成**：Phase 0〜5 完了。以降は月末cronで無人実行され、田口が下書きを確認→発行・送付。

## 確定した接続情報（メモ）

- 事業所: 株式会社 和銅農園 / **company_id = 1506256**
- アプリ: 和銅農園 請求書自動作成 / Client ID = 759738689736560 / コールバックURL = `urn:ietf:wg:oauth:2.0:oob`
- 必要なアプリ権限: **[freee請求書] 全帳票種別（参照＋更新）** ＋ [会計] 事業所（参照）
- 取得スコープ: `accounting:companies:read accounting:docs:read invoice:docs:read invoice:docs:write`
- 請求書テンプレート: 1961370（窓付き） / 1897124（窓付き封筒）
- 対象開始: 2025-08-01（当期）

---

## Phase 0: 環境構築 ✅

- VPS（Xserver 162.43.32.67）、GitHub / Supabase、MCP接続を整備。

## Phase 1: 設計 ✅

- `docs/system-design.md`、`supabase/migrations/0001_init.sql`（partners / billing_runs / invoice_links / issue_jobs / freee_tokens）。
- 合算方式確定（APIに合算なし → 明細集計して POST /invoices）。

## Phase 2: freee OAuth連携 ✅

- アプリ登録・認可・トークン保存。権限ハマり: [freee請求書]全帳票種別の参照＋更新を付与→再認可で invoice:docs:write 取得。

## Phase 3: 納品書の取得と明細集計 ✅

- `src/freee_api.py`：対象月の納品書取得・明細取得。
- 名寄せ（`src/aliases.py`）を適用し、取引先ごとに明細を合算。
- ドライランで検証済み（2026-06 / 2026-03）。

## Phase 4: 請求書の下書き作成と記録 ✅

- `POST /invoices` で下書き作成（税区分等は納品書から引継）。
- `issue_jobs` / `invoice_links` に記録。テスト: 秩鉄商事 INV-0000000952（53,676円）。

## Phase 5: 月次締めバッチの統合 ✅

- `src/billing.py` 本体 ＋ `scripts/run_billing.py`。依存ゼロ（標準ライブラリ）。
- トークン自動更新（`src/freee_token.py`）、Supabaseアクセス（`src/store.py`、REST）。
- 二重作成防止2段：①`invoice_links`既出の納品書除外 ②freee上で代表取引先×当月の請求書があれば除外。
- **cron設定済み**：毎月末日 23:30 に当月分を下書き作成し `billing.log` に追記。手動実行（2026-07、納品0件）で正常終了を確認。

## Phase 6: 運用開始・検証 ⬜（進行中）

- 初回本番は 7月末。生成された下書きを freee画面で確認（金額・明細・宛先・税区分）→ 発行・送付。
- 運用注意: バッチに任せる取引先は手動で二重に請求書化しない。

## Phase 7: 将来拡張 ⬜（保留）

- 自動送付（方式A）、見積書対応、取引先別締め日、確認用UIなど。

---

## 直近の次アクション

1. **テスト下書きの取消**：freeeで INV-0000000952（秩鉄商事のテスト）を削除。
2. **7月末**：cronが自動実行。`billing.log` と freeeの下書きを確認し、問題なければ発行・送付。
