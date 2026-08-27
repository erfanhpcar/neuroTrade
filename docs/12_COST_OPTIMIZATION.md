# ۱۲ — بهینه‌سازی هزینه API (هدف: زیر ۲۰ دلار در ماه)

این سند **سیاست اجباری** پروژه برای مصرف LLM است. بدون این سه لایه، اجرای چرخه هر ۵ دقیقه با Claude می‌تواند به **۱۵۰+ دلار در ماه** برسد. با پیاده‌سازی دقیق زیر، هدف **۱۵–۲۰ دلار** واقع‌بینانه است.

---

## اصل معماری: Claude فقط با ماشه (Trigger-Based)

| لایه | هزینه | نقش |
|------|--------|-----|
| **لایه ۰ — Scheduler** | رایگان | فرکانس چرخه بر اساس تایم‌فریم |
| **لایه ۱ — Zone Gate (Pandas)** | رایگان | آیا قیمت وارد Supply/Demand شده؟ |
| **لایه ۲ — LLM سبک** | ارزان | سنتیمنت اخبار (DeepSeek / gpt-4o-mini) |
| **لایه ۳ — LLM سنگین** | گران (محدود) | Strategist + Decision **فقط** اگر Zone Gate = true |

---

## 🛠️ ترفند ۱ — بهینه‌سازی فرکانس بر اساس تایم‌فریم

استراتژی روی **1H** یا **4H** است؛ اجرای کامل خط لوله هر **۵ دقیقه** بیهوده است — کندل بسته نشده و ساختار تکنیکال معنادار عوض نمی‌شود.

### قانون سخت‌کد در `config.py`

| `DEFAULT_TIMEFRAME` | `CYCLE_INTERVAL_SECONDS` | معادل |
|---------------------|--------------------------|--------|
| `15m` | `300` | ۵ دقیقه (استثنا — فقط اگر عمداً اسکالپ شود) |
| `1h` | `900` | **۱۵ دقیقه** (پیش‌فرض تولید) |
| `4h` | `1800` | **۳۰ دقیقه** |

```python
TIMEFRAME_CYCLE_MAP = {
    "15m": 300,
    "1h": 900,
    "4h": 1800,
}

def resolve_cycle_interval(timeframe: str) -> int:
    return TIMEFRAME_CYCLE_MAP.get(timeframe.lower(), 900)
```

### اثر تقریبی روی هزینه

- ۵ دقیقه → ~۸۶۴۰ چرخه LLM در ماه (اگر هر چرخه Claude بزند)
- ۱۵ دقیقه → ~۲۸۸۰ چرخه (**÷۳**)
- ۳۰ دقیقه → ~۱۴۴۰ چرخه (**÷۶**)

> **نکته:** Retriever (قیمت لایو برای Zone Gate) می‌تواند هر ۱–۲ دقیقه فقط `fetch_ticker` بزند **بدون** فراخوانی LLM — جزئیات در ترفند ۲.

---

## 🛠️ ترفند ۲ — معماری ماشه زون (Trigger-Based Processing)

### مشکل

فراخوانی Claude در هر چرخه برای جمله‌ای مثل *«قیمت وسط رنج است — HOLD»* هزینه‌بر و بی‌فایده است.

### راهکار

1. **`core/zone_trigger.py`** (Pandas/Numpy، بدون LLM):
   - از آخرین N کندل، زون‌های Supply/Demand را با قواعد ریاضی SMC (همان منطق بک‌تست `06`) محاسبه کند.
   - قیمت لایو (`last` یا close کندل جاری) را با بازه `[zone_low, zone_high]` مقایسه کند.
2. اگر **`zone_hit == false`** → چرخه **همان‌جا تمام** شود:
   - WebSocket: `AGENT_STATUS_UPDATE` با پیام `"Idle — price mid-range, LLM skipped"`
   - **هیچ** درخواست Anthropic/OpenRouter برای Strategist/Decision
3. اگر **`zone_hit == true`** → LangGraph از نود `strategist` ادامه دهد.

### شبه‌کد Gate

```python
def should_invoke_llm(candles: list, last_price: float, buffer_pct: float = 0.001) -> tuple[bool, str]:
    zones = compute_supply_demand_zones(candles)  # خروجی: list[{type, low, high}]
    for z in zones:
        low, high = z["low"], z["high"]
        pad = (high - low) * buffer_pct
        if low - pad <= last_price <= high + pad:
            return True, f"ZONE_HIT:{z['type']}"
    return False, "MID_RANGE"
```

### اثر

- در بازار رنج، بیشتر چرخه‌ها در Gate متوقف می‌شوند → **تا ~۹۰٪** کاهش فراخوانی Claude.
- این همان الگوی **Hybrid Backtest** در `06_BACKTESTING.md` است؛ در لایو یکسان پیاده شود.

### گراف به‌روز LangGraph

```
START → retrieve_data → zone_gate
                              ├─ (false) → log_skip → END
                              └─ (true)  → [strategist, sentiment] → decision → risk → ...
```

---

## 🛠️ ترفند ۳ — OpenRouter (یک کلید، چند مدل)

همه LLMها از `AsyncOpenAI(base_url=openrouter)` — جزئیات: `07_EXTERNAL_SERVICES.md`.

| نود | env | پیش‌فرض ارزان/قدرتمند |
|-----|-----|------------------------|
| `sentiment` | `SENTIMENT_MODEL` | `deepseek/deepseek-v3` |
| `strategist` | `STRATEGIST_MODEL` | `anthropic/claude-3.5-sonnet` یا DeepSeek برای صرفه‌جویی |
| `decision` | `DECISION_MODEL` | `anthropic/claude-3.5-sonnet` (Trigger) |

**صرفه‌جویی:** `SENTIMENT_MODEL=deepseek/deepseek-v3`؛ Strategist/Decision را فقط روی رویدادهای `zone_hit` صدا بزن.

**Failover:** `LLM_FALLBACK_MODEL=deepseek/deepseek-r1` روی 402/429.

---

## بودجه ماهانه (تخمین مهندسی)

فرض: `1h` تایم‌فریم، چرخه ۱۵ دقیقه، Zone Gate ۹۰٪ رد، ~۳۰ رویداد LLM/ماه با Decision روی Claude:

| آیتم | تخمین |
|------|--------|
| Claude Sonnet (Decision × ~۳۰) | ~۸–۱۲$ |
| DeepSeek / mini (Sentiment + Strategist × ~۳۰) | ~۲–۵$ |
| CryptoPanic + Testnet | رایگان / ناچیز |
| **جمع** | **~۱۵–۲۰$** |

برای مانیتور: فیلد `ai_cost_usd` در لاگ چرخه یا جدول `agent_signals` (اختیاری فاز ۲).

---

## چک‌لیست پیاده‌سازی (اجباری)

- [ ] `CYCLE_INTERVAL_SECONDS` از `TIMEFRAME_CYCLE_MAP` — نه مقدار ثابت ۳۰۰
- [ ] `core/zone_trigger.py` قبل از هر LLM در `graph.py`
- [ ] `LLM_TIER=trigger` در config — Strategist/Decision بدون `zone_hit` unreachable
- [ ] `OPENROUTER_API_KEY` + `core/llm_client.py`
- [ ] داشبورد: شمارنده «چرخه‌های ردشده / LLM فراخوانی‌شده» (اختیاری)

---

## اسناد مرتبط

- `02_AGENT_PROTOCOLS.md` — گراف و چرخه
- `06_BACKTESTING.md` — همان Gate در بک‌تست
- `07_EXTERNAL_SERVICES.md` — OpenRouter و DeepSeek
- `08_PROMPT_DICTIONARY.md` — مدل هر ایجنت
- `11_IMPLEMENTATION_GUIDE.md` — متغیرهای env
