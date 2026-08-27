# ۱۳ — تأمل پس از حادثه (Post-Mortem Reflection)

این سند نحوه «باهوش‌تر شدن» سیستم را **بدون یادگیری زنده** در حین ترید تعریف می‌کند.

## اصل طلایی: ممنوعیت Live Learning

| مجاز | ممنوع |
|------|--------|
| لاگ کامل هر معامله | تغییر `core/risk.py` یا فرمول پوزیشن‌سایز در حین باز بودن پوزیشن |
| ممیزی آفلاین آخر هفته | Fine-tune مدل یا RL روی استریم زنده |
| **پیشنهاد** تغییر پرامپت/وزن (در انتظار تأیید شما) | اعمال **خودکار** پرامپت پس از ممیزی |
| به‌روزرسانی پرامپت **فقط پس از Approve در UI** | بازنویسی کد قطعی Risk Firewall توسط LLM |

> اشتباه رایج ربات‌های معامله‌گر: اجازه به AI برای یادگیری زنده — این کار ریسک تغییر ناخواستهٔ مدیریت سرمایه را بالا می‌برد.

---

## الف) جعبه سیاه تریدها (The Ledger — «داستان معامله»)

پس از **بسته شدن** هر پوزیشن (سود یا ضرر)، بک‌اند یک رکورد کامل می‌سازد:

| فیلد | محتوا |
|------|--------|
| `trade_id` | UUID پوزیشن |
| `war_room_transcript` | تمام چت‌ها و دلایل ایجنت‌ها در چرخهٔ ورود (Strategist، Sentiment، Decision) |
| `sentiment_at_entry` | `sentiment_score` در ثانیهٔ ورود |
| `sentiment_at_exit` | همان فیلد در خروج |
| `candles_snapshot` | OHLCV دقیق لحظه ورود/خروج (JSON یا Parquet کوچک) |
| `zone_context` | `zone_score`, `zone_freshness`, محدوده S/D |
| `confluence_flags` | آیا LTF sweep/MSS بود؟ |
| `pnl_pct` | نتیجه نهایی بر حسب درصد |
| `closed_at` | timestamp |

### ذخیره‌سازی

- **فایل:** `backend/data/ledger/{trade_id}.json` — یک فایل per trade («داستان معامله»)
- **دیتابیس:** جدول `trade_ledger` در `04_DATA_SCHEMAS.md` (ایندکس برای ممیزی هفتگی)

اسکریپت: `backend/app/core/trade_ledger.py` — فراخوانی از نود `on_position_closed` پس از `TRADE_UPDATE` با `status=CLOSED`.

---

## ب) ایجنت ممیزی هفتگی (Weekly Audit Agent)

### زمان‌بندی

- **Cron:** شنبه یا یکشنبه ۰۲:۰۰ UTC (یا وقتی بازار کریپتو رنج / بازارهای سنتی بسته‌اند)
- **نوع:** اسکریپت **آفلاین** — `backend/scripts/weekly_audit.py`
- **هیچ اردری** در این بازه صادر نمی‌شود

### مدل و نقش

| متغیر env | پیش‌فرض |
|-----------|---------|
| `AUDIT_MODEL` | `anthropic/claude-3.5-sonnet` |

ایجنت **منتقد** با پرامپت سخت‌گیر — فقط معاملات **ضررده** هفته را از `trade_ledger` می‌خواند.

### نمونه خروجی تحلیل (متنی در گزارش)

> در معامله شماره ۴، در زون تقاضای ۱H وارد شدیم و استاپ خوردیم. بررسی لایو نشان می‌دهد روند ۴H به‌شدت نزولی بود و زون ۱H قدرت کافی نداشت. ایجنت سنتیمنت واگرایی منفی اخبار را دست‌کم گرفته بود.

خروجی: `backend/data/audit_reports/YYYY-WW.md` + JSON ساختاریافته `audit_findings.json`.

---

## ج) پیشنهاد تغییر پرامپت — بدون اعمال خودکار

پس از ممیزی، سیستم **هیچ فایل پرامپتی را مستقیماً نمی‌نویسد**. فقط **پیشنهاد (Proposal)** در دیتابیس ثبت می‌کند تا شما در داشبورد بررسی کنید — همان الگوی Human-in-the-loop مثل `SEMI` برای سیگنال‌ها.

| هدف | فایل هدف (پس از Approve) | مثال پیشنهاد |
|-----|--------------------------|--------------|
| Strategist | `prompts/active/strategist.system.md` | قانون HTF نزولی + استثناء کف‌سازی |
| Decision | `prompts/active/decision.system.md` | سخت‌گیری بیشتر روی `confluence_ready` |
| Zone Gate | `config/agent_weights.yaml` | `min_zone_score: 65 → 72` |

**مسیرهای پرامپت:**

| پوشه | نقش |
|------|-----|
| `prompts/baseline/` | نسخهٔ اولیه — تحت Git، مرجع بازگشت |
| `prompts/active/` | نسخهٔ **در حال اجرا** — فقط با `POST .../approve` به‌روز می‌شود |
| `data/proposals/` | پیش‌نویس JSON ممیزی — تا تأیید شما |

`apply_prompt_tuning.py` **فقط** از endpoint تأیید فراخوانی می‌شود — **هرگز** از cron ممیزی.

---

## د) حفاظت در برابر بیش‌برازش پرامپت (Prompt Overfitting Guardrail)

### سناریوی خطر

مارکت یک هفته **آنومال** رفتار می‌کند (خبر شوک، رنج بی‌سابقه، شکست همهٔ زون‌های S/D). ممیزی هفتهٔ بعد پرامپت‌ها را برای «همان هفته» تنظیم می‌کند. هفتهٔ بعد بازار نرمال می‌شود؛ ربات با قوانین overfit ضرر می‌دهد.

### خط قرمز معماری (قفل‌شده)

| # | قانون |
|---|--------|
| 1 | **هیچ** تغییر پرامپت/YAML بدون `POST /api/prompt-proposals/{id}/approve` از UI |
| 2 | ممیزی فقط `status=PENDING` می‌سازد — `apply_*` در cron **ممنوع** |
| 3 | `core/risk.py` و فرمول‌های `03` — خارج از محدودهٔ پیشنهاد؛ LLM حق ویرایش ندارد |
| 4 | حداکثر **۳ پیشنهاد فعال** در هر گزارش هفتگی (جلوگیری از بازنویسی کل استراتژی) |
| 5 | پیشنهادها پس از **۱۴ روز** منقضی (`EXPIRED`) — بدون تأیید، دور انداخته می‌شوند |
| 6 | هر Approve یک **snapshot** در `prompt_versions` — Rollback یک کلیک |
| 7 | اگر ممیزی `market_regime=ANOMALOUS` برچسب زد → UI **هشدار زرد** اجباری قبل از Approve |

### تشخیص هفتهٔ آنومال (برچسب ممیزی)

ایجنت ممیزی در `audit_findings.json` باید فیلد زیر را پر کند:

```json
{
  "week_id": "2026-W20",
  "market_regime": "NORMAL | ANOMALOUS",
  "regime_reason": "Win rate 12% across all tickers; BTC 3-sigma range expansion; news shock CPI+geopolitical same day",
  "proposals": [ ... ]
}
```

Heuristic قطعی (پیش از LLM) در `weekly_audit.py`:

- `ANOMALOUS` اگر: `loss_count >= 5` **و** (`avg_atr_pct` هفته > ۱.۵× میانگین ۸ هفته قبل **یا** `win_rate < 25%`)
- در غیر این صورت `NORMAL`

پیشنهادهای هفتهٔ `ANOMALOUS` در UI با بنر: *«این تغییرات برای بازار غیرعادی بود — تأیید با احتیاط»*.

### جریان تأیید در فرانت‌اند

```
weekly_audit.py → INSERT prompt_change_proposals (PENDING)
                         ↓
              WebSocket: PROMPT_TUNING_REQUEST
                         ↓
        /settings/prompt-tuning — Diff قبل/بعد + دلیل ممیزی
                         ↓
     [Approve] → apply_prompt_tuning.py → prompts/active + prompt_versions
     [Reject]  → status=REJECTED + reason (لاگ برای ممیزی بعدی)
     [Rollback]→ بازگشت به version قبلی (بدون LLM)
```

همانند `ApprovalModal` برای سیگنال — **دو مرحله** برای Approve (Dialog تأیید + در هفته ANOMALOUS متن هشدار اضافی).

### API و UI

- REST: `10_REST_API.md` — `GET/POST prompt-proposals`
- جدول: `04_DATA_SCHEMAS.md` — `prompt_change_proposals`, `prompt_versions`
- صفحه: `05_DASHBOARD_UI.md` — `PromptTuningReview.tsx`

---

## جریان کلی (مثل تریدر حرفه‌ای)

```
معامله زنده → Ledger
       ↓
آخر هفته: Weekly Audit → proposals (PENDING) — نه اعمال
       ↓
شما در UI: Diff + Approve/Reject/Rollback
       ↓
فقط پس از Approve → prompts/active به‌روز → هفته بعد ترید با قوانین جدید
```

## اسناد مرتبط

- استراتژی S/D و Confluence: `02_AGENT_PROTOCOLS.md` بخش ۰
- پرامپت‌های پایه: `08_PROMPT_DICTIONARY.md` بخش ۴
- اسکیما Ledger: `04_DATA_SCHEMAS.md`
- پیاده‌سازی: `11_IMPLEMENTATION_GUIDE.md` فاز G
- API تأیید پیشنهاد: `10_REST_API.md`
- UI بررسی: `05_DASHBOARD_UI.md`
