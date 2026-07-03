# freee-invoice システム設計書

最終更新: 2026-07-03 / ステータス: 初版（設計合意済み）

## 1. 概要

和銅農園の掛け売り・月末締めの請求業務を、freee請求書APIを使って半自動化するアプリ。
freee上の**納品書を正データ**とし、月末締めで取引先ごとの納品書を合算して**請求書の下書き（draft）を自動作成**する。
田口が内容を目視確認し、freee上で発行・メール送付を行う。

設計の基本思想は「**二重管理をしない**」こと。納品明細はfreeeに任せ、Supabaseは締め・紐付け・発行管理という薄い制御レイヤーに徹する。

## 2. 業務要件

| 項目 | 内容 |
|------|------|
| 業態 | 和銅農園（農産物の掛け売り） |
| 請求方式 | 都度の納品を月末締めで合算し、取引先ごとに請求書1枚 |
| 締め | 月末締め |
| 納品書 | 今後は納品のたびに必ずfreeeで作成する（請求の網羅性を運用で担保） |
| 単価 | 納品書側で確定済み（アプリは金額計算に関与しない） |
| 自動化レベル | 下書き作成まで自動。確認・発行・送付は田口が手動（方式B） |
| 送付 | 当面は田口がfreee画面で実行。自動送付（方式A）は将来オプション |

## 3. 利用するfreee API

freee**請求書**API（`https://developer.freee.co.jp/reference/iv`）を使用する。

> 注意: freee**会計**APIの請求書・見積書の新規作成（POST）は2023年10月に廃止された。
> 作成系は freee請求書API に移行済み。freee請求書で発行すると会計側に取引が連携される。

主に使うエンドポイント:

| エンドポイント | 用途 |
|----------------|------|
| `GET /delivery_slips` | 当月・取引先・未請求の納品書一覧を取得 |
| `GET /delivery_slips/{id}` | 納品書の明細取得（合算元データ） |
| `GET /invoices/templates` | 請求書の帳票テンプレート取得（作成時に必須） |
| `POST /invoices` | 請求書を `status=draft` で作成 |
| `GET /invoices/{id}` | 作成した請求書の確認 |

認証は OAuth2.0。アクセストークン／リフレッシュトークンと有効期限を管理し、期限前に自動リフレッシュする。

### 合算の実装方式（要最終確認）

- **第1候補**: freeeの合算機能をAPIから利用し、納品書IDを渡して請求書化する。
- **フォールバック**: 合算がAPIで直接できない場合、`GET /delivery_slips` で明細を読み、集計して `POST /invoices` で作成する（結果は同じ）。
- API概要には納品書・請求書それぞれのCRUDのみ記載があり、合算専用エンドポイントは未確認。実装着手時にアクセストークンを用いて詳細リファレンスで確定する（→ §8 TODO）。

> `status=draft` 以外で作成すると会計取引が自動生成される。本アプリは必ず `draft` で作成する。

## 4. アーキテクチャ

```
freee（納品書=正） ──①当月・取引先ごとの納品書をGET──▶ 発行ワーカー（VPS）
                                                          │
                                    ②取引先単位で合算 → 請求書をdraft作成（POST /invoices）
                                                          │
Supabase ◀──── ③どの納品書をどの請求書にまとめたか記録（締め・冪等・二重請求防止）
                                                          │
              ④田口がfreee画面で目視確認 → 発行 → メール送付（会計取引が確定）
```

| 構成要素 | 役割 |
|----------|------|
| freee請求書 | 納品書（正データ）の保持。請求書の作成先・発行・送付。会計連携。 |
| 発行ワーカー（VPS 162.43.32.67） | 月末締めバッチ。納品書の取得・合算・請求書draft作成・結果の書き戻し。 |
| Supabase(Postgres) | 締め実行・請求書↔納品書の紐付け・発行ジョブ・OAuthトークンの管理。 |

## 5. データ設計（Supabase）

納品明細そのものはfreeeが正のため、Supabaseは制御データのみを持つ。

### partners（取引先）
| カラム | 型 | 説明 |
|--------|----|----|
| id | uuid (PK) | 内部ID |
| freee_partner_id | text | freee側取引先ID |
| name | text | 取引先名 |
| default_invoice_template_id | text | 請求書作成に使う帳票テンプレートID |
| closing_day | int | 締め日（当面は月末=末日固定。将来の取引先別締め用） |
| created_at / updated_at | timestamptz | |

### billing_runs（締め処理の実行単位）
| カラム | 型 | 説明 |
|--------|----|----|
| id | uuid (PK) | |
| period_ym | text | 対象年月（例: 2026-07） |
| status | text | `running` / `drafted` / `failed` |
| started_at / finished_at | timestamptz | |

### invoice_links（請求書 ↔ 納品書の対応）※二重請求防止の要
| カラム | 型 | 説明 |
|--------|----|----|
| id | uuid (PK) | |
| billing_run_id | uuid (FK) | どの締めで作られたか |
| partner_id | uuid (FK) | 取引先 |
| freee_invoice_id | text | 作成した請求書ID |
| freee_delivery_slip_id | text | 束ねた納品書ID |
| period_ym | text | 対象年月 |
| UNIQUE | | (freee_delivery_slip_id) で同一納品書の二重取り込みを禁止 |

### issue_jobs（発行ジョブ）
| カラム | 型 | 説明 |
|--------|----|----|
| id | uuid (PK) | |
| billing_run_id | uuid (FK) | |
| partner_id | uuid (FK) | |
| status | text | `pending` / `drafted` / `failed` |
| idempotency_key | text | UNIQUE(period_ym, partner_id) で二重発行防止 |
| freee_response | jsonb | freeeレスポンス生データ |
| error | text | エラー内容（生データ） |

### freee_tokens（OAuth）
| カラム | 型 | 説明 |
|--------|----|----|
| id | uuid (PK) | |
| access_token | text | |
| refresh_token | text | |
| expires_at | timestamptz | |
| company_id | text | freee事業所ID |

## 6. 処理フロー（月末締めバッチ）

1. `billing_runs` を1件作成（status=running）。
2. トークンの有効期限を確認し、必要ならリフレッシュ。
3. 取引先ごとに、当月・未請求の納品書を `GET /delivery_slips` で取得。
   - `invoice_links` に既出の納品書IDは除外（二重請求防止）。
4. 取引先単位で納品書を合算し、`POST /invoices`（status=draft, template_id, partner_id）で下書き作成。
5. 作成結果を `issue_jobs` と `invoice_links` に書き戻す。
6. 全件終了で `billing_runs.status=drafted`。1件でも失敗があれば該当ジョブを `failed` として残し、再実行可能にする。
7. 「今回請求に含めた納品書の一覧（取引先別）」を確認用に出力し、田口へ提示。

田口の手作業（アプリ範囲外）: freee画面で目視確認 → 発行 → メール送付。

## 7. 状態遷移

- billing_run: `running → drafted`（失敗時は `failed`、再実行で `running` に戻す）
- issue_job: `pending → drafted`（失敗時 `failed` → 再実行で `pending`）
- 冪等性: `issue_jobs.idempotency_key = (period_ym, partner_id)` と `invoice_links` の納品書UNIQUEで、再実行しても二重発行・二重請求が起きない。

## 8. 漏れ・重複対策

- **漏れ**: 請求の網羅性は「納品ごとに必ず納品書を作る」運用で担保。加えて締め時に取引先別の対象納品書リストを提示し、発行前に目視チェックできるようにする。
- **重複**: `invoice_links` の納品書ID UNIQUE制約で、翌月以降に同じ納品書を再度拾わない。

## 9. 将来拡張

- **方式A（自動送付）**: 下書き精度が安定したら、承認後にアプリがfreee経由でメール送付まで自動化。処理フロー上「作成」と「送付」を分離しておくため、切替はフラグ1つで可能。
- 見積書（`/quotations`）対応。
- 取引先別の締め日対応（`partners.closing_day` を活用）。

## 10. 未確定事項 / TODO

- [ ] 合算のAPI可否をアクセストークンで詳細リファレンス上で最終確認（§3）。
- [ ] 請求書の帳票テンプレートID（`GET /invoices/templates`）の取得と取引先への割当。
- [ ] 取引先マスタ（freee_partner_id との対応）の初期整備。
- [ ] 「未請求」の判定方法の確定（freee側の状態か、`invoice_links` 突合か）。
- [ ] OAuthトークンの保管方式（Supabase暗号化 or VPS環境変数）の決定。
