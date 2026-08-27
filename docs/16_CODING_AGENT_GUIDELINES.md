# 16 — Coding Agent Guidelines (Cursor + Codex)

این سند توضیح انسانی سیاست کدنویسی neuroTrade برای کار با Cursor و Codex است. قواعد اجرایی واقعی در فایل‌های repository نگه‌داری می‌شوند تا agentها آن‌ها را به‌صورت پایدار دریافت کنند.

## 1. فایل‌های قانون

| فایل | مخاطب | نقش |
|---|---|---|
| `/AGENTS.md` | Codex + Cursor | قواعد مشترک کل repository |
| `/backend/AGENTS.md` | Codex + Cursor | قواعد Python/Quant/Risk/Execution |
| `/frontend/AGENTS.md` | Codex + Cursor | قواعد Next.js/TypeScript/Dashboard |
| `/.cursor/rules/00-neurotrade-core.mdc` | Cursor | Rule همیشه فعال و ارجاع به قواعد مشترک |
| `/.cursor/rules/backend-python.mdc` | Cursor | Rule scoped برای backend Python |
| `/.cursor/rules/frontend-nextjs.mdc` | Cursor | Rule scoped برای frontend |
| `/docs/*.md` | انسان + هر agent | Source of Truth معماری و قراردادها |

اصل مهم: قوانین مشترک را در `AGENTS.md` نگه می‌داریم تا رفتار پروژه وابسته به یک IDE/Agent خاص نشود. Cursor ruleهای `.mdc` بیشتر برای scope و تضمین بارگذاری context هستند.

## 2. Policy قبل از کدنویسی

برای هر task غیرجزئی agent باید:

1. `AGENTS.md` را بخواند.
2. `docs/00_INDEX.md` و سندهای subsystem مربوط را بخواند.
3. کد موجود را inspect کند.
4. فایل‌های مورد تغییر و test plan را مشخص کند.
5. تغییر را فقط در scope همان concern نگه دارد.

### چه زمانی agent باید قبل از implementation متوقف شود؟

اگر task شامل یکی از موارد زیر باشد و تصمیم آن قبلاً در docs تأیید نشده باشد:

- تغییر معماری اصلی؛
- تغییر قوانین Strategy یا Risk؛
- تغییر semantics اجرای Order؛
- schema migration مخرب؛
- تغییر REST/WebSocket contract؛
- dependency جدید مهم؛
- exchange/data provider جدید؛
- تغییر حالت‌های PAPER/SEMI/FULL؛
- تغییر HALT/FLATTEN behavior.

در این موارد agent ابتدا گزینه‌ها، trade-off و plan را ارائه می‌کند و منتظر تصمیم می‌ماند.

برای taskهای مشخص داخل یک Phase تأییدشده، agent می‌تواند پس از plan کوتاه implementation را ادامه دهد.

## 3. اصول کدنویسی مشترک

### سادگی

- کد واضح و قابل تست بر abstraction هوشمندانه ترجیح دارد.
- abstraction جدید فقط برای boundary واقعی یا duplication اثبات‌شده.
- refactor نامرتبط همراه feature ممنوع.
- side effectها باید در boundaryهای مشخص باشند.

### Type Safety

Backend:
- Python type hints در boundaryها و APIهای عمومی.
- Domainها framework-independent.

Frontend:
- TypeScript strict.
- `any` فقط در boundary محدود و با narrowing/validation فوری.

### Time و Number

- زمان در boundary/persistence همیشه timezone-aware UTC.
- `Decimal` برای price/quantity/balance/fee/PnL/risk/notional قابل اجرا و persisted.
- float برای research/vectorized math مجاز است ولی نباید بدون validation وارد Execution/Persistence شود.

## 4. قوانین مخصوص Trading System

این بخش از style guide مهم‌تر است.

### Strategy

```text
MarketSnapshot → Strategy → Signal
```

Strategy:
- network call ندارد؛
- database call ندارد؛
- order ارسال نمی‌کند؛
- final position sizing انجام نمی‌دهد؛
- hidden clock/random state ندارد؛
- برای dataset+config یکسان deterministic است.

همان implementation باید Backtest و Live/Paper را تغذیه کند.

### Risk

```text
Signal → Portfolio State → RiskDecision
```

- هیچ Order بدون APPROVED RiskDecision.
- Risk logic deterministic.
- concurrent signalها باید atomic risk reservation داشته باشند.
- تغییر Risk behavior بدون test و مستندات ممنوع.

### Execution

```text
Risk-approved OrderIntent → Execution Adapter → Exchange
```

- `client_order_id` unique و persisted.
- ambiguous timeout = ابتدا reconciliation، سپس تصمیم برای retry.
- blind retry روی create order ممنوع.
- partial fill، cancel، restart و exchange discrepancy باید state transition مشخص داشته باشند.

### Reconciliation

Exchange برای state واقعی account مرجع نهایی است. Database باید به‌طور دوره‌ای با balance/order/fill/position واقعی reconcile شود و discrepancy را event/error قابل مشاهده کند.

## 5. Safe Defaults

تمام نمونه‌ها، local development و testها با این اصل شروع می‌شوند:

```env
TRADING_MODE=PAPER
```

هیچ agent نباید صرفاً برای «تست کردن» mode را به live تغییر دهد.

Exchange API:

```text
Read               فقط در صورت نیاز
Futures Trading    فقط Test/Demo/SEMI/Live تأییدشده
Transfer           disabled
Withdrawal         ALWAYS disabled
```

Secretها در Git، prompt output، screenshot/log یا browser bundle ممنوع.

## 6. تست مورد انتظار

| Subsystem | حداقل تست |
|---|---|
| Strategy | deterministic replay، no-look-ahead، missing data |
| Backtest | reproducibility، fees/slippage، ambiguous candles |
| Risk | limits، boundaries، invalid data، concurrent reservation |
| Execution | duplicate، timeout، partial fill، cancel، restart |
| Reconciliation | DB/exchange divergence و recovery |
| API | contract/status/error tests |
| Frontend | reconnect/resync، stale state، dangerous confirmations |

Unit testها نباید به اینترنت عمومی وابسته باشند. sandbox/testnet integration test باید opt-in باشد.

## 7. Definition of Done برای Agent

Agent زمانی task را Done اعلام می‌کند که:

- implementation داخل scope باشد؛
- docs در صورت تغییر contract/architecture هماهنگ شده باشند؛
- tests لازم نوشته/به‌روزرسانی شده باشند؛
- lint/typecheck/tests مربوط اجرا شده باشند؛
- نتیجه دقیق commandها گزارش شود؛
- known risk یا کاری که نتوانسته اجرا کند شفاف اعلام شود.

گفتن «should work» یا «looks correct» بدون validation کافی نیست.

## 8. Git Policy

- یک PR = یک Phase یا concern مشخص.
- تغییرات نامرتبط دست‌نخورده بمانند.
- agent بدون درخواست صریح main را merge نمی‌کند.
- commitهای کوچک و توصیفی ترجیح دارند:
  - `feat:`
  - `fix:`
  - `test:`
  - `docs:`
  - `refactor:`
  - `chore:`

Generated market data، secrets، local database، `.env` واقعی، virtualenv، `node_modules` و build output در Git ممنوع.

## 9. Prompt استاندارد برای شروع Phase

این prompt برای Cursor یا Codex قابل استفاده است:

```text
Read AGENTS.md, docs/00_INDEX.md, and the documents referenced for this phase before editing anything.

Inspect the current repository and then provide:
1. the architecture constraints relevant to this phase,
2. the exact files you expect to create/change,
3. a small implementation plan,
4. a test/verification plan,
5. any conflict or missing decision in the docs.

If the task requires a new architectural, strategy, risk, execution, schema, API, dependency, or exchange decision that is not already approved, stop and ask before implementing it.

Otherwise implement only the requested phase/concern. Do not refactor unrelated code.
After implementation run the repository-defined checks and report exact results, changed files, remaining risks, and the next smallest step.
```

## 10. به‌روزرسانی قوانین

Ruleها دائمی ولی غیرقابل تغییر نیستند. اگر Cursor/Codex یک خطای تکرارشونده ایجاد کرد:

1. علت را مشخص کنید؛
2. اگر مشکل عمومی است `AGENTS.md` را اصلاح کنید؛
3. اگر فقط backend/frontend است nested `AGENTS.md` را اصلاح کنید؛
4. اگر رفتار مخصوص Cursor/context loading است `.cursor/rules/*.mdc` را اصلاح کنید؛
5. Rule را کوتاه، مشخص و قابل آزمون نگه دارید.

هدف Ruleها زیاد کردن متن prompt نیست؛ هدف جلوگیری از خطاهای تکراری و حفاظت از boundaryهای مالی و معماری پروژه است.
