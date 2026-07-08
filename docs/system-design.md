# freee-invoice システム設計書

最終更新: 2026-07-06 / ステータス: **実装完了（MVP稼働・月末cron運用中）**

関連: [development-roadmap.md](./development-roadmap.md) / [partner-aliases.md](./partner-aliases.md)

## 1. 概要

和銅農園の掛け売り・月末締めの請求業務を、freee請求書APIを使って半自動化するアプリ。
freee上の**納品書を正データ**とし、月末締めで取引先ごとの納品書の明細を集計して**請求書の下書き（draft）を自動作成**する。
田口が内容を目視確認し、freee上で発行・メール送付を行う（方式B）。

基本思想は「**二重管理をしない**」こと。納品明細はfreeeに任せ、Supabaseは締め・紐付け・発行管理という薄い制御レイヤーに徒する。

## 2. 業務要件

| 項目 | 内容 |
|------|------|
| 業態 | 和銅農園（農産物の掛け売り） |
| 請求方式 | 都度の納品を月末締めで集計し、取引先ごとに請求書1枚 |
| 会計期（一期） | 2025-08-01 〜 2026-07-31 |
| 対象開始 | **2025-08-01（当期）**。前期（〜2025-07）の納品書は対象外 |
| 締め | 月末締め |
| 納品書 | 納品のたびにfreeeで作成（請求の網羅性を運用で担保） |
| 単価 | 納品書側で確定済み（アプリは金額計算に関与せず明細を転記） |
| 自動化レベル | 下書き作成まで自動。確認・発行・送付は手動（方式B） |
| 送付 | 当面は田口がfreee画面で実行。自動送付（方式A）は将来 |

## 3. 利用するfreee API

freee**請求書**API（エンドポイント `https://api.freee.co.jp/iv`）を使用。

> 会計APIの帳票作成(POST)は2023-10に廃止。作成系は freee請求書API に移行済み。
> 会計UIの帳票機能も内部は freee請求書 で動いており、事業所で freee請求書 を有効化して利用する。

主なエンドポイント:

| エンドポイント | 用途 |
|----------------|------|
| `GET /delivery_slips` | 対象月の納品書一覧（日付で絞り込み） |
| `GET /delivery_slips/{id}` | 納品書の明細取得（集計元） |
| `GET /invoices` | 既存請求書の一覧（重複作成のガードに使用） |
| `POST /invoices` | 請求書を明細付きで作成（下書き） |

### 認証・権限・接続情報

- 認証: OAuth2.0。トークンエンドポイント `https://accounts.secure.freee.co.jp/public_api/token`。
- アクセストークンは短命、リフレッシュトークンは使うたびにローテート→毎回保存。
- 必要なアプリ権限: **[freee請求書] 全帳票種別（参照＋更新）** ＋ [会計] 事業所（参照）。
- 取得スコープ: `accounting:companies:read accounting:docs:read invoice:docs:read invoice:docs:write`。
- 事業所: 株式会社 和銅農園 / **company_id = 1506256**。
- 請求書テンプレート: 1961370（窓付き） / 1897124（窓付き封筒）。既定は 1961370。
- API制限: 1時隓1500回・1勆30回・1日3000回。月次バッチの規模では十分収まる。

### 請求書作成方式

freeeの「合算」はWeb画面の機能でAPIには無い（OpenAPI原本で確認済み）。`POST /invoices` は明細（lines）を直接渡す方式のみ。
したがって本アプリは「納品書をGET→明細を集計→POST」で作る。

`InvoiceRequest` 必須: `company_id` / `billing_date` / `tax_entry_method` / `tax_fraction` / `withholding_tax_entry_method` / `partner_title` / `lines`。
税区分・端数処理は集計元の納品書から引き継ぐ。

## 4. アーキテクチャ

```
freee（納品書=正） ──①対象月の納品書をGET──▶ 締めバッチ（VPS / cron）
                                            │
           ②名寄せ→取引先ごとに明細を集計→請求書をdraft作成 (POST /invoices)
                                            │
Supabase ◀─ ③どの納品書をどの請求書にまとめたか記録（締め・冕等・二重防止）
                                            │
              ④田口がfreee画面で目視確認 → 発行 → メール送付（会計取引が確定）
```

| 構成要素 | 役割 | 費用 |
|----------|------|------|
| freee請求書 | 納品書（正）の保持。請求書の作成先・発行・送付。会計連携 | 既存（無料プラン可） |
| VPS（162.43.32.67） | 月末締めバッチ(cron)。納品書取得・集計・draft作成・書き戻し | 契約済（追加なし） |
| Supabase(Postgres) | トークン・締め・紐付け・発行ジョブの管理 | 無料枠 |

> 追加の月額費用は発生しない。

### コード構成（リポジトリ wadou-sd/freee-invoice）

依存ライブラリなし（Python標準ライブラリのみ）。

- `src/config.py` … `.env`と環境変数の読み込み
- `src/store.py` … Supabase(PostgREST)アクセス（service_roleキーでRLSをバイパス）
- `src/freee_token.py` … アクセストークンの取得・自動リフレッシュ
- `src/freee_api.py` … iv API（納品書取得・請求書作成等）
- `src/aliases.py` … 取引先の名寄せ（partner_id→代表pid）
- `src/billing.py` … 締めバッチ本体
- `scripts/run_billing.py` … 実行入口（`--dry-run`、月指定可）
- `supabase/migrations/0001_init.sql` … DBスキーマ
- `.env`（VPSのみ・Git非管理）… FREEE_CLIENT_ID/SECRET, FREEE_COMPANY_ID, SUPABASE_URL/SERVICE_KEY, BILLING_START_DATE

### 実行

- 手動: `python3 scripts/run_billing.py [YYYY-MM] [--dry-run]`
- 自動: VPSのcronで毎月末日 23:30 に当月分を実行し `billing.log` に追記。

## 5. データ設計（Supabase）

納品明細自体はfreeeが正のため、Supabaseは制御データのみを持つ。（migration: `0001_init.sql`）

- **partners** … 取引先マスタ。v1では未使用（名寄せは `src/aliases.py` の定数で保持）。
- **billing_runs** … 締め実行単位。`period_ym`(UNIQUE) / `status`(running/drafted/failed)。
- **invoice_links** … 請求書↔納品書の対応。`freee_delivery_slip_id`(UNIQUE) で同一納品書の二重取込み禁止。v1では `partner_id`(FK) はnull。
- **issue_jobs** … 発行ジョブ。`idempotency_key = "{period_ym}:{代表pid}"`(UNIQUE)で二重作成防止。`freee_response`(jsonb)/`error`。
- **freee_tokens** … OAuthトークン（access/refresh/expires_at/company_id）。

全テーブルRLS有効（ポリシー無し）。VPSバッチは service_role(secret) キーで接続しRLSをバイパス。

## 6. 処理フロー（月末締めバッチ `billing.run`）

1. 有効なアクセストークンを取得（期限が近ければリフレッシュしSupabaseに保存）。
2. `GET /delivery_slips` で対象月の納品書を取得。`BILLING_START_DATE`(2025-08-01)以降に絞る。
3. **二重防止①**: `invoice_links` に既出の納品書IDは除外。
4. 名寄せ（`aliases.representative_pid`）を適用し、代表取引先ごとにグループ化。
5. **二重防止②**: freee上で「代表取引先 × 当月(billing_dateの月)」の請求書が既にあるグループは除外（手動作成との重複防止）。
6. 各グループで納品書明細を合算し、`POST /invoices`（代表pid・当月末日billing_date・税区分は納品書引継）で下書き作成。
7. 結果を `issue_jobs`（drafted/failed）と `invoice_links` に記録。`billing_runs` を更新。
8. 実行ログを `billing.log` に出力（作成件数・スキップ・エラー）。

田口の手作業（アプリ範囲外）: freee画面で目視確認 → 発行 → メール送付。

## 7. 状態遷移・冕等性

- billing_run: `running → drafted`（失敗ありで `failed`）。period_ymはget-or-createで再実行可。
- issue_job: `drafted` / `failed`。idempotency_key で同月・同取引先の二重を回避。
- 再実行しても invoice_links（納品書UNIQUE）＋freee既存請求書チェックにより二重作成・二重請求は起きない。

## 8. 漏れ・重複対策

- **漏れ**: 「納品ごとに必ず納品書を作る」運用で担保。ログで対象件数を確認可能。
- **重複（2段ガード）**: ①`invoice_links` 既出の納品書を除外、②freee上に「代表取引先×当月」の請求書があれば除外。
- 運用注意: ②はbilling_dateの月で判定するため、バッチに任せる取引先を手動で二重に請求書化しない（しても下書き確認で気づける）。

## 9. 取引先の名寄せ

同一取引先がfreee上で別 partner_id に分裂している分を、`src/aliases.py` で代表pidに寄せる（詳細は [partner-aliases.md](./partner-aliases.md)）。
統合6組: 佐野挙利・森田浩司・埼玉県知事・大宮マルシェ・一富士・日本生命。分離: 平沼/平沼康代、西川/西川和子、県立2校。

## 10. 将来拡張

- 方式A（自動送付）: 承認後にメール送付まで自動化（`partner_sending_method` 等）。
- 見積書対応、取引先別締め日、確認用UI、名寄せのDBテーブル化（partner_aliases）など。

## 11. 残 TODO

- テスト下書き INV-0000000952（秩鉄商事）の取消。
- 大宮マルシェの代表pid最終確認（現状 60509611）。
- 7月末初回本番の検証（Phase 6）。
