# ۱۰ — قرارداد REST و WebSocket

این سند **قرارداد دقیق** بین `backend` و `frontend` است. هر endpoint باید دقیقاً همین شکل را برگرداند/بپذیرد.

## پایه

| مورد | مقدار |
|------|--------|
| Base URL (dev) | `http://localhost:8000` |
| WebSocket (dev) | `ws://localhost:8000/ws/dashboard` |
| Content-Type | `application/json` |
| Auth (فاز ۱) | بدون JWT — فقط localhost / شبکه خصوصی. فاز ۲: API Key در header |

---

## REST Endpoints

### `GET /api/health`

```json
{ "status": "ok", "system_state": "ACTIVE" | "SUSPENDED" | "IDLE" }
```

### `GET /api/settings`

خواندن تنظیمات از `system_settings` (یک ردیف، `id=1`).

```json
{
  "is_active": false,
  "trading_mode": "SEMI",
  "risk_per_trade": 1.0,
  "max_daily_drawdown": 3.0,
  "daily_drawdown_used_pct": 0.8,
  "open_positions_count": 2
}
```

### `PATCH /api/settings`

```json
{
  "is_active": true,
  "trading_mode": "FULL",
  "risk_per_trade": 1.0
}
```

**قوانین:** `risk_per_trade` فقط بین `0.5` و `1.5`. تغییر به `FULL` فقط اگر `is_active=true`.

### `GET /api/signals?limit=50&offset=0&ticker=BTC/USDT`

```json
{
  "items": [
    {
      "id": "uuid",
      "ticker": "BTC/USDT",
      "timeframe": "1H",
      "decision": "BUY",
      "sentiment_score": 0.65,
      "reasoning": "متن استدلال...",
      "market_structure": {},
      "created_at": "2026-05-21T10:00:00Z"
    }
  ],
  "total": 120
}
```

### `GET /api/trades?status=OPEN`

```json
{
  "items": [
    {
      "id": "uuid",
      "signal_id": "uuid",
      "ticker": "BTC/USDT",
      "side": "LONG",
      "entry_price": 64200.0,
      "stop_loss": 63500.0,
      "take_profit": 66000.0,
      "position_size": 0.045,
      "status": "OPEN",
      "pnl_usd": 45.2,
      "opened_at": "2026-05-21T10:05:00Z"
    }
  ]
}
```

### `POST /api/signals/{signal_id}/approve` (فقط SEMI)

بدنه خالی. پس از Risk تأییدشده، اردر به صرافی می‌رود.

```json
{ "ok": true, "exchange_order_id": "123456" }
```

خطا: `409` اگر سیگنال منقضی یا قبلاً اجرا شده.

### `POST /api/signals/{signal_id}/reject` (فقط SEMI)

```json
{ "reason": "اختیاری — دلیل رد تریدر" }
```

پاسخ: `{ "ok": true }`

### `GET /api/prompt-proposals?status=PENDING`

لیست پیشنهادهای ممیزی در انتظار تأیید — `13` بخش د.

```json
{
  "items": [
    {
      "id": "uuid",
      "week_id": "2026-W20",
      "market_regime": "ANOMALOUS",
      "target_file": "prompts/active/strategist.system.md",
      "change_type": "APPEND_RULE",
      "content_before": "...",
      "content_after": "...",
      "audit_reasoning": "Trade #4 lost: 4H bearish dominated 1H demand...",
      "status": "PENDING",
      "expires_at": "2026-06-04T00:00:00Z",
      "created_at": "2026-05-21T02:00:00Z"
    }
  ],
  "total": 2
}
```

### `POST /api/prompt-proposals/{proposal_id}/approve`

**تنها مسیر مجاز** برای نوشتن `prompts/active/` و `agent_weights.yaml`. بدنه خالی.

```json
{ "ok": true, "version_label": "v2026-W20-a1", "target_file": "prompts/active/strategist.system.md" }
```

خطا: `409` اگر `EXPIRED` یا `ANOMALOUS` بدون `confirm_anomalous=true` در query (فاز ۱: همیشه `?confirm_anomalous=true` در UI برای هفته آنومال).

### `POST /api/prompt-proposals/{proposal_id}/reject`

```json
{ "reason": "قانون بیش‌ازحد سخت — فقط برای هفته CPI بود" }
```

پاسخ: `{ "ok": true }`

### `POST /api/prompt-proposals/rollback`

بازگشت به آخرین `prompt_versions` فعال — **بدون LLM**.

```json
{ "target_file": "prompts/active/decision.system.md" }
```

```json
{ "ok": true, "restored_version": "v2026-W19-b2" }
```

### `POST /api/emergency/kill-switch`

**بدون body.** بالاترین اولویت.

```json
{
  "ok": true,
  "closed_positions": 2,
  "canceled_orders": 1,
  "system_state": "SUSPENDED"
}
```

---

## WebSocket

### اتصال

کلاینت به `ws://localhost:8000/ws/dashboard` وصل می‌شود. سرور پس از اتصال یک پکت `CONNECTED` می‌فرستد.

### قالب عمومی همه پکت‌ها

```json
{
  "event": "EVENT_NAME",
  "timestamp": "2026-05-21T10:00:00Z",
  "data": { }
}
```

### رویدادها

| event | زمان ارسال |
|-------|------------|
| `CONNECTED` | بلافاصله پس از handshake |
| `AGENT_STATUS_UPDATE` | هر مرحله LangGraph |
| `SIGNAL_APPROVAL_REQUEST` | SEMI + سیگنال معتبر پس از Risk |
| `TRADE_UPDATE` | باز/بسته شدن پوزیشن یا تغییر PnL |
| `BALANCE_UPDATE` | پس از `fetch_balance` هر چرخه |
| `SYSTEM_STATE_CHANGE` | تغییر `is_active` / Kill-Switch / daily lock |
| `PROMPT_TUNING_REQUEST` | پایان ممیزی هفتگی — پیشنهادها PENDING (بدون اعمال خودکار) |

#### `SIGNAL_APPROVAL_REQUEST` — همان `04_DATA_SCHEMAS` + فیلدهای اجباری:

```json
{
  "event": "SIGNAL_APPROVAL_REQUEST",
  "data": {
    "signal_id": "uuid",
    "ticker": "BTC/USDT",
    "side": "LONG",
    "entry_price": 64200.0,
    "stop_loss": 63500.0,
    "take_profit": 66000.0,
    "calculated_size": 0.045,
    "risk_reward_ratio": 2.57,
    "reasoning": "متن کامل..."
  }
}
```

#### `TRADE_UPDATE`

```json
{
  "event": "TRADE_UPDATE",
  "data": {
    "trade_id": "uuid",
    "ticker": "BTC/USDT",
    "side": "LONG",
    "status": "OPEN",
    "pnl_usd": 45.2,
    "current_price": 64300.0
  }
}
```

#### `BALANCE_UPDATE`

```json
{
  "event": "BALANCE_UPDATE",
  "data": {
    "total_balance_usd": 10450.0,
    "daily_drawdown_pct": 0.8,
    "max_daily_drawdown_pct": 3.0,
    "open_risk_pct": 2.0
  }
}
```

### Reconnect (فرانت‌اند)

- Exponential backoff: `1s → 2s → 4s → …` حداکثر `30s`
- پس از reconnect: `GET /api/settings` + `GET /api/trades?status=OPEN` برای sync

---

## TypeScript — `frontend/src/types/index.ts`

این تایپ‌ها باید **۱:۱** با قرارداد بالا باشند:

```typescript
export type TradingMode = "SEMI" | "FULL";
export type SystemState = "ACTIVE" | "SUSPENDED" | "IDLE";
export type SignalDecision = "BUY" | "SELL" | "HOLD";
export type TradeSide = "LONG" | "SHORT";
export type TradeStatus = "OPEN" | "CLOSED" | "CANCELED";

export interface WsEnvelope<T = unknown> {
  event: string;
  timestamp: string;
  data: T;
}

export interface SignalApprovalRequest {
  signal_id: string;
  ticker: string;
  side: TradeSide;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  calculated_size: number;
  risk_reward_ratio: number;
  reasoning: string;
}

export type PromptProposalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";
export type MarketRegime = "NORMAL" | "ANOMALOUS";

export interface PromptTuningRequest {
  week_id: string;
  market_regime: MarketRegime;
  regime_reason: string;
  proposal_count: number;
  proposals_preview: Array<{ id: string; target_file: string; summary: string }>;
}

export interface PromptChangeProposal {
  id: string;
  week_id: string;
  market_regime: MarketRegime;
  target_file: string;
  change_type: "APPEND_RULE" | "REPLACE_SECTION" | "WEIGHT_YAML";
  content_before: string;
  content_after: string;
  audit_reasoning: string;
  status: PromptProposalStatus;
  expires_at: string;
  created_at: string;
}
```

---

## کدهای خطای HTTP

| کد | معنی |
|----|------|
| 400 | body نامعتبر |
| 409 | تضاد وضعیت (مثلاً approve روی سیگنال منقضی) |
| 423 | سیستم SUSPENDED — فقط kill-switch recovery مجاز |
| 503 | صرافی یا LLM در دسترس نیست |
