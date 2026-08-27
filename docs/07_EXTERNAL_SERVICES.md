این سند مشخصات فنی، متدهای احراز هویت، اِندپوینت‌ها (Endpoints) و استراتژی مدیریت خطای تمام سرویس‌های واسط که سیستم با آن‌ها تعامل دارد را تعریف می‌کند.

## ۱. لایه معاملات و داده‌های بازار (Exchange Trading API)

سیستم برای ارتباط با صرافی‌ها از هاب **CCXT (CryptoCurrency eXchange Trading)** استفاده می‌کند. ابزار ارجح برای تست، صرافی **Bybit Testnet** یا **Binance Testnet** است.

- **نوع احراز هویت:** HMAC-SHA256 API Key & Secret Key.
- **متد اتصال بک‌اند:** نمونه‌سازی به صورت `async` (غیرهمگام) جهت جلوگیری از بلاک شدن واکشی داده‌ها.

### اِندپوینت‌های حیاتی مورد استفاده از طریق CCXT:


|                           |                    |                                          |
| ------------------------- | ------------------ | ---------------------------------------- |
| **عملکرد سیستم**          | **متد داخلی CCXT** | **اِندپوینت پایه صرافی (Binance/Bybit)** |
| دریافت کندل‌های زنده      | `fetch_ohlcv()`    | `/api/v3/klines`                         |
| بررسی موجودی حساب         | `fetch_balance()`  | `/api/v3/account`                        |
| ارسال اردر (Market/Limit) | `create_order()`   | `/api/v3/order` (POST)                   |
| لغو اردرهای باز           | `cancel_order()`   | `/api/v3/order` (DELETE)                 |


### پروتکل مدیریت نرخ درخواست (Rate Limit Protocol):

صرافی‌ها محدودیت شدید روی تعداد درخواست در دقیقه (مثلاً ۱۲۰۰ ریکوئست) دارند.

> **قانون سخت‌کد شده بک‌اند:** برنامه باید برای تمام ایجنت‌ها از مکانیزم **Rate-Limiter (Leaky Bucket)** استفاده کند. فاصله بین درخواست‌های مداوم تکنیکال برای دریافت دیتای بازار نباید کمتر از ۵۰۰ میلی‌ثانیه باشد.

## ۲. لایه اخبار و پایش سنتیمنت (News & Sentiment API)

برای اینکه ایجنتِ فاندامنتال بتواند اخبار را دریافت کند، سیستم به فیدهای خبری اختصاصی کریپتو متصل می‌شود.

### سرویس اول: CryptoPanic API

- **وظیفه:** دریافت لحظه‌ای اخبار، توییت‌های تاثیرگذار و رسانه‌های کریپتویی.
- **نوع احراز هویت:** API Token به عنوان پارامتر کوئری (`&auth_token=`).
- **اِندپوینت واکشی اخبار:**
  Plaintext
  ```
  GET https://cryptopanic.com/api/v1/posts/?auth_token=<TOKEN>&currencies=BTC,ETH&filter=hot

  ```
- **فیلتر هوشمند:** بک‌اند پایتون فیلد `filter=hot` را برای دریافت اخبار تاییدشده و پربازدید ارسال می‌کند تا نویز بازار خنثی شود.

## ۳. هوش مصنوعی — OpenRouter (تک درگاه واحد)

تمام ایجنت‌ها از **یک کلاینت** و **یک API Key** استفاده می‌کنند. تعویض مدل = تغییر رشته در `.env`، بدون تغییر کد ایجنت.

سیاست هزینه و Zone Gate: `12_COST_OPTIMIZATION.md` — LLM فقط وقتی `zone_hit=true`.

### کلاینت واحد (`backend/app/core/llm_client.py`)

```python
from openai import AsyncOpenAI
from app.config import settings

ai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

# فراخوانی نمونه در هر ایجنت:
# response = await ai_client.chat.completions.create(
#     model=settings.STRATEGIST_MODEL,
#     messages=[...],
#     temperature=0.0,
# )
```

### مدل‌ها — فقط از `.env`

| متغیر env | پیش‌فرض پیشنهادی | نود |
|-----------|------------------|-----|
| `STRATEGIST_MODEL` | `anthropic/claude-3.5-sonnet` | تحلیل تکنیکال SMC |
| `SENTIMENT_MODEL` | `deepseek/deepseek-v3` | اخبار و سنتیمنت (ارزان و دقیق) |
| `DECISION_MODEL` | `anthropic/claude-3.5-sonnet` | داور نهایی BUY/SELL/HOLD |
| `LLM_FALLBACK_MODEL` | `deepseek/deepseek-r1` | Failover روی 402/429 |

```env
OPENROUTER_API_KEY=sk-or-...
STRATEGIST_MODEL=anthropic/claude-3.5-sonnet
SENTIMENT_MODEL=deepseek/deepseek-v3
DECISION_MODEL=anthropic/claude-3.5-sonnet
LLM_FALLBACK_MODEL=deepseek/deepseek-r1
```

> **مانور روی Reasoning Models:** برای A/B فقط `DECISION_MODEL=deepseek/deepseek-r1` بگذار — همان `ai_client`، همان کد.

### هدرهای توصیه‌شده OpenRouter (اختیاری)

```python
extra_headers = {
    "HTTP-Referer": "https://neurotrade.local",
    "X-Title": "neuroTrade",
}
```

### قوانین فراخوانی

1. هیچ `chat.completions` قبل از `zone_gate`.
2. `temperature=0.0` برای همه ایجنت‌ها.
3. خروجی فقط JSON — اعتبارسنجی Pydantic قبل از Risk.

## ۴. لایه اطلاع‌رسانی تریدر (Notification & Telemetry)

برای اینکه در هر لحظه (حتی وقتی پای داشبورد Next.js نیستی) از تصمیمات سیستم باخبر شوی، یک ربات تلگرام به سیستم متصل می‌شود.

- **سرویس:** Telegram Bot API
- **نوع احراز هویت:** Bot Token اختصاصی از BotFather.
- **مکانیزم ارسال:** متد متنی لایو (Async HTTP POST) به محض باز شدن یا بسته شدن هر پوزیشن.
- **فرمت پکت تلگرام:**

Plaintext

```
    https://api.telegram.org/bot<BOT_TOKEN>/sendMessage
    Payload: {"chat_id": "<YOUR_TELEGRAM_ID>", "text": "🚨 AI SIGNAL: LONG BTC/USDT @ 64,200\nSL: 63,500\nReason: Market structure shifted on 1H charts.", "parse_mode": "Markdown"}
    ```

---

## ۵. استراتژی بازگشت از خطا (API Fallback & Resilience Rules)

در کدهای پایتون (FastAPI)، تمام درخواست‌ها به سرویس‌های بالا باید در کلاژهای `try-except` با پروتکل‌های زیر قفل شوند:

1.  **خطای شبکه صرافی (Timeout):** اگر کانکشن صرافی بیش از ۵ ثانیه پاسخ نداد، سیستم اردر را معلق کرده، تلاش مجدد (Retry) تا ۳ بار با فاصله ۲ ثانیه انجام می‌دهد. اگر همچنان قطع بود، وضعیت به `ERROR` تغییر کرده و تلگرام هشدار صادر می‌کند.
2.  **اتمام کریدیت OpenRouter (402/429):** همان ایجنت با `LLM_FALLBACK_MODEL` یک‌بار Retry؛ لاگ + تلگرام. معاملات باز تحت Risk مدیریت می‌شوند.

---

اسناد مرتبط: `08_PROMPT_DICTIONARY.md`، `12_COST_OPTIMIZATION.md`، `10_REST_API.md`، `11_IMPLEMENTATION_GUIDE.md`.

