این سند ساختار دقیق لایه ذخیره‌سازی داده‌ها (PostgreSQL) و لایه مخابره اطلاعات زنده (WebSocket) را برای یکپارچگی کامل سیستم مشخص می‌کند.

## ۱. ساختار جداول پایگاه داده (PostgreSQL Schemas)

برای ذخیره لاگ تصمیمات و تاریخچه معاملات به ۳ جدول اصلی نیاز داریم. ساختار SQL آنها به این صورت قفل می‌شود:

### جدول اول: تنظیمات سیستم و ریسک (system_settings)

این جدول وضعیت فعلی بات، تنظیمات ریسک و دروپ‌داون‌ها را نگه می‌دارد.

SQL

```
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    is_active BOOLEAN DEFAULT FALSE,          -- روشن یا خاموش بودن کل سیستم
    trading_mode VARCHAR(20) DEFAULT 'SEMI', -- 'SEMI' (نیمه اتوماتیک) یا 'FULL' (تمام اتوماتیک)
    risk_per_trade NUMERIC(4, 2) DEFAULT 1.00,-- درصد ریسک در هر معامله (مثلا 1.00%)
    max_daily_drawdown NUMERIC(4, 2) DEFAULT 3.00,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

### جدول دوم: تحلیل‌ها و سیگنال‌های ایجنت‌ها (agent_signals)

تمام استدلال‌ها و خروجی‌های میانی متنی ایجنت‌ها اینجا ذخیره می‌شود تا در فرانت‌انداز تاریخچه تصمیم‌گیری قابل دیدن باشد.

SQL

```
CREATE TABLE agent_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,              -- مثلا "BTC/USDT"
    timeframe VARCHAR(10) NOT NULL,           -- "1H"
    market_structure JSONB NOT NULL,          -- خروجی زون‌های عرضه و تقاضا
    sentiment_score NUMERIC(3, 2) NOT NULL,   -- امتیاز اخبار
    decision VARCHAR(10) NOT NULL,            -- BUY, SELL, HOLD
    reasoning TEXT NOT NULL,                  -- متن استدلال نهایی مدل برای نمایش به کاربر
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

```

### جدول سوم: جعبه سیاه — داستان معامله (trade_ledger)

هر پوزیشن **بسته‌شده** یک رکورد «داستان معامله» دارد — `13_POST_MORTEM_REFLECTION.md`.

SQL

```
CREATE TABLE trade_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trade_positions(id),
    ticker VARCHAR(20) NOT NULL,
    war_room_transcript JSONB NOT NULL,       -- چت و دلایل ایجنت‌ها در ورود
    sentiment_at_entry NUMERIC(3, 2),
    sentiment_at_exit NUMERIC(3, 2),
    candles_snapshot JSONB NOT NULL,          -- OHLCV ورود/خروج
    zone_context JSONB NOT NULL,              -- zone_score, freshness, S/D range
    confluence_flags JSONB NOT NULL,          -- ltf_sweep, mss, confluence_ready
    pnl_pct NUMERIC(8, 4) NOT NULL,
    ledger_file_path VARCHAR(512),            -- مسیر data/ledger/{uuid}.json
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trade_ledger_closed_week ON trade_ledger (created_at)
    WHERE pnl_pct < 0;  -- برای ممیزی هفتگی ضررها
```

### جدول چهارم: تاریخچه پوزیشن‌ها (trade_positions)

وضعیت اردرهای ارسال شده به صرافی و خروجی سود/زیان پوزیشن‌ها.

SQL

```
CREATE TABLE trade_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES agent_signals(id),
    exchange_order_id VARCHAR(100),           -- شناسه اردر در صرافی (از CCXT)
    ticker VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,                -- LONG or SHORT
    entry_price NUMERIC(18, 8) NOT NULL,
    stop_loss NUMERIC(18, 8) NOT NULL,
    take_profit NUMERIC(18, 8) NOT NULL,
    position_size NUMERIC(18, 8) NOT NULL,    -- حجم پوزیشن معامله شده
    status VARCHAR(20) DEFAULT 'OPEN',        -- 'OPEN', 'CLOSED', 'CANCELED'
    pnl_usd NUMERIC(18, 4) DEFAULT 0.0000,    -- سود یا زیان نهایی پس از بسته شدن
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

```

### جدول پنجم: پیشنهاد تغییر پرامپت (prompt_change_proposals)

ممیزی هفتگی فقط ردیف `PENDING` می‌سازد — اعمال با Approve در UI — `13` بخش د.

SQL

```
CREATE TABLE prompt_change_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_id VARCHAR(10) NOT NULL,             -- مثلا "2026-W20"
    market_regime VARCHAR(20) NOT NULL,       -- NORMAL | ANOMALOUS
    target_file VARCHAR(255) NOT NULL,        -- prompts/active/strategist.system.md
    change_type VARCHAR(20) NOT NULL,         -- APPEND_RULE | REPLACE_SECTION | WEIGHT_YAML
    content_before TEXT NOT NULL,
    content_after TEXT NOT NULL,
    audit_reasoning TEXT NOT NULL,            -- چرا ممیزی این را پیشنهاد داد
    status VARCHAR(20) DEFAULT 'PENDING',     -- PENDING | APPROVED | REJECTED | EXPIRED
    reject_reason TEXT,
    approved_by VARCHAR(100),                 -- شناسه اپراتور (فاز ۲: user id)
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_prompt_proposals_pending ON prompt_change_proposals (status, created_at)
    WHERE status = 'PENDING';
```

### جدول ششم: نسخه‌های تأییدشده پرامپت (prompt_versions)

برای Rollback — هر Approve یک snapshot.

SQL

```
CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES prompt_change_proposals(id),
    target_file VARCHAR(255) NOT NULL,
    content_snapshot TEXT NOT NULL,
    version_label VARCHAR(50) NOT NULL,       -- مثلا "v2026-W20-a1"
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## ۲. ساختار پکت‌های وب‌ساکت (WebSocket Payloads)

بک‌اند FastAPI در هر چرخه تحلیل (یا تغییر پوزیشن در صرافی)، یک پکت JSON روی کانال وب‌ساکت به فرانت‌انداز برودکست (Broadcast) می‌کند.

### پکت اول: به‌روزرسانی زنده وضعیت ایجنت‌ها (AGENT_STATUS_UPDATE)

زمانی که هر ایجنت کارش تمام می‌شود، فرانت‌انداز این وضعیت را زنده به کاربر نشان می‌دهد:

JSON

```
{
  "event": "AGENT_STATUS_UPDATE",
  "data": {
    "current_agent": "Technical Strategist",
    "status": "PROCESSING", 
    "message": "Analyzing 4H Supply/Demand zones for BTC/USDT..."
  }
}

```

### پکت دوم: به‌روزرسانی پوزیشن (TRADE_UPDATE)

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

### پکت سوم: موجودی و دروپ‌داون (BALANCE_UPDATE)

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

### پکت چهارم: صدور سیگنال جدید در حالت نیمه‌اتوماتیک (SIGNAL_APPROVAL_REQUEST)

اگر سیستم روی حالت نیمه‌اتوماتیک (SEMI) باشد، این پکت پاپ‌آپ تاییدیه را در فرانت‌انداز فعال می‌کند:

JSON

```
{
  "event": "SIGNAL_APPROVAL_REQUEST",
  "data": {
    "signal_id": "d3b07384-d113-4ec2-a5d8-c71d32847a92",
    "ticker": "BTC/USDT",
    "side": "LONG",
    "entry_price": 64200.0,
    "stop_loss": 63500.0,
    "take_profit": 66000.0,
    "calculated_size": 0.045,
    "reasoning": "Price swept internal liquidity and tapped into 1H Demand base. Funding rate is neutral, sentiment is positive after CPI report."
  }
}

```

### پکت پنجم: درخواست بررسی پیشنهاد پرامپت (PROMPT_TUNING_REQUEST)

پس از `weekly_audit.py` — بدون اعمال خودکار:

JSON

```
{
  "event": "PROMPT_TUNING_REQUEST",
  "data": {
    "week_id": "2026-W20",
    "market_regime": "ANOMALOUS",
    "regime_reason": "Win rate 12%; range expansion 3-sigma",
    "proposal_count": 2,
    "proposals_preview": [
      {
        "id": "uuid",
        "target_file": "prompts/active/strategist.system.md",
        "summary": "Ignore 1H demand if 4H strongly bearish unless triple bottom"
      }
    ]
  }
}
```

**REST API** (approve/reject/kill-switch/settings/prompt-proposals): `10_REST_API.md`.

**Redis:** کانال `ws:broadcast` — بک‌اند پس از هر رویداد JSON را publish می‌کند؛ handler WebSocket در FastAPI subscribe و به کلاینت‌ها forward می‌کند.