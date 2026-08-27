# 08 — AI Extension (Optional, Later)

## وضعیت

AI در V0/V1 dependency پروژه نیست. هیچ API key هوش مصنوعی برای research/backtest/paper/testnet اولیه لازم نیست.

## نکته مهم درباره Cursor/Codex

استفاده از **Cursor یا Codex برای نوشتن کد پروژه** با استفاده از **AI داخل محصول neuroTrade** دو موضوع جداست.

- Cursor/Codex ابزار توسعه هستند و باید Ruleهای `AGENTS.md`, nested `AGENTS.md`, `.cursor/rules/` و `16_CODING_AGENT_GUIDELINES.md` را رعایت کنند.
- محصول neuroTrade در MVP هیچ LLM را برای تصمیم معاملاتی فراخوانی نمی‌کند.

بنابراین وجود coding agent به معنی اضافه‌شدن OpenAI/OpenRouter/Claude API به runtime پروژه نیست.

## کاربردهای مجاز آینده

پس از baseline deterministic و فقط به صورت آزمایشی:

- توضیح یک trade/signal برای اپراتور؛
- post-mortem معاملات؛
- خلاصه‌کردن backtest/sensitivity results؛
- research assistant برای تولید hypothesis؛
- anomaly triage برای لاگ/عملیات؛
- تحلیل اخبار به عنوان research feature جدا، در صورت داشتن OOS evidence.

## کاربردهای ممنوع بدون evidence/تصمیم جدید

- LLM مستقیماً `create_order` را صدا بزند؛
- LLM Risk Engine را override کند؛
- LLM config/strategy active را خودکار تغییر دهد؛
- LLM از نتایج چند معامله live فوراً «یاد بگیرد» و production logic را عوض کند؛
- یک confidence متنی بدون baseline کمی باعث trade شود.

## معماری آینده

```text
Deterministic Trading Platform ──> Logs / Results / Ledger
                                      │
                                      ▼
                                AI Research Layer
                                ├─ Explain
                                ├─ Post-Mortem
                                └─ Hypothesis
```

مسیر Execution:

```text
Market → Strategy → Risk → Execution
```

بدون AI باقی می‌ماند مگر یک ADR/نسخه آینده صریحاً خلاف آن را تصویب کند.

## Evaluation

هر feature AI باید با baseline بدون AI مقایسه شود:

- OOS / walk-forward؛
- forward/paper؛
- latency؛
- API failure behavior؛
- cost؛
- incremental expectancy / risk؛
- reproducibility.

اگر بهبود قابل اندازه‌گیری ندارد، AI dependency اضافه نشود.
