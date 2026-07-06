# freee-invoice 開発ロードマップ

最終更新: 2026-07-06

関連ドキュメント: [system-design.md](./system-design.md)

## 進め方の原則

- **費用をかけない** … 既存VPS（162.43.32.67）＋ Supabase無料枠 ＋ freee で完結。新規の有料サービスは追加しない。
- **小さく確認しながら** … 各フェーズは「動く最小」を作り、田口が確認してから次へ。
- **安全側で** … Supabase書き込み・VPS書き込みは事前承認。請求書はまず下書き（draft）まで。発行・送付は田口が手動（方式B）。

## 進捗サマリ

| Phase | 内容 | 状態 |
|-------|------|------|
| 0 | 環境構築 | ✅ 完了 |
| 1 | 設計（全体像・データ設計・API方針・DBスキーマ） | ✅ 完了 |
| 2 | freee OAuth連携（トークン取得・保存・更新） | ✅ 完了 |
| 3 | 納品書の取得と明細集計 | ⬜ 未着手（次） |
| 4 | 請求書の下書き作成と記録 | ⬜ 未着手 |
| 5 | 月次締めバッチの統合（cron） | ⬜ 未着手 |
| 6 | 運用開始・検証 | ⬜ 未着手 |
| 7 | 将来拡張 | ⬜ 保留 |

## 確定した接続情報（メモ）

- 事業所: 株式会社 和銅農園 / **company_id = 1506256**
- アプリ: 和銅農園 請求書自動作成 / Client ID = 759738689736560 / コールバックURL = `urn:ietf:wg:oauth:2.0:oob`
- 必要なアプリ権限: **[freee請求書] 全帳票種別（参照＋更新）** ＋ [会計] 事業所（参照）
- 取得スコープ: `accounting:companies:read accounting:docs:read invoice:docs:read invoice:docs:write`
- 請求書テンプレート: 1961370（窓付き） / 1897124（窓付き封筒）
- トークンエンドポイント: `https://accounts.secure.freee.co.jp/public_api/token`
- APIエンドポイント: `https://api.freee.co.jp/iv`

---

## Phase 0: 環境構築 ✅

- Node.js / Python / SSH、GitHub / Supabase、VPS（Xserver 162.43.32.67）、MCP接続を整備済み。
- リポジトリ `wadou-sd/freee-invoice` と VPS `/root/projects/freee-invoice` を連携。

## Phase 1: 設計 ✅

- `docs/system-design.md`：全体像・データ設計・処理フロー・状態遷移。
- 合算方式を確定（APIに合算なし → `GET /delivery_slips` で取得し明細集計 → `POST /invoices`）。
- `supabase/migrations/0001_init.sql`：partners / billing_runs / invoice_links / issue_jobs / freee_tokens を作成済み。

## Phase 2: freee OAuth連携 ✅

**目的**: freee請求書APIを叩ける状態にする。→ 達成。

- [x] freeeでアプリ登録し client_id / client_secret を取得。
- [x] 認可フロー（OAuth2.0, oob）でアクセストークン／リフレッシュトークンを取得。
- [x] トークンを `freee_tokens` に保存（company_id 含む）。
- [x] 疎通確認：`GET /invoices/templates`・`GET /delivery_slips` が200。
- [ ] 有効期限前の自動リフレッシュ処理（バッチ実装時に組み込む）。

**ハマりどころ（記録）**: 会計側の帳票権限は「参照」のみ（会計API帳票POST廃止の名残）。請求書の作成には別途 **[freee請求書] 全帳票種別（参照＋更新）** の権限が必要で、付与＋再認可で `invoice:docs:write` が付き解決した。

## Phase 3: 納品書の取得と明細集計 ⬜（次に着手）

**目的**: 請求書の元データを作る。

- [ ] `GET /delivery_slips` の絞り込み（取引先・期間）と明細の中身を実データで確認。
- [ ] 当月・未請求の納品書を取得（`invoice_links` 既出分は除外）。
- [ ] 取引先単位で明細（lines）を集計するロジック（金額は納品書の値を転記）。
- [ ] 「今回の対象納品書一覧（取引先別）」を確認用に出力。

## Phase 4: 請求書の下書き作成と記録 ⬜

**目的**: freeeに下書きを作り、結果を記録する。

- [ ] `POST /invoices`（lines・template_id・partner_id 等）で下書き作成。
- [ ] 成否を `issue_jobs`、紐付けを `invoice_links` に書き戻し。
- [ ] 冪等性の確認（同じ月・取引先で二重作成されないこと）。
- [ ] エラー時は `failed` で残し、再実行で復帰できること。

## Phase 5: 月次締めバッチの統合 ⬜

**目的**: 月末に自動で下書きまで作る。

- [ ] Phase 2〜4 を1本のバッチにまとめる。
- [ ] VPSのcronで月末実行（例：毎月末 or 翌月1日）。
- [ ] `billing_runs` で実行単位を管理。ログ出力。
- [ ] 実行結果（対象納品書一覧・作成件数・エラー）を田口が確認できる形で残す。

## Phase 6: 運用開始・検証 ⬜

- [ ] テスト用の取引先で下書き作成 → freee画面で内容確認。
- [ ] 金額・明細・宛先・税区分が納品書と一致することを検証。
- [ ] 問題なければ本番運用開始（田口が確認 → 発行 → メール送付）。

## Phase 7: 将来拡張 ⬜（保留）

- 自動送付（方式A）：承認後にアプリがメール送付まで実行（`partner_sending_method` 等）。
- 見積書（`/quotations`）対応。
- 取引先別の締め日対応（`partners.closing_day`）。
- 簡易な確認用UI（必要になれば）。

---

## 直近の次アクション

1. **Phase 3**：`GET /delivery_slips` の絞り込み（取引先・期間）と明細構造を実データで確認し、取引先単位の明細集計ロジックを設計する。
