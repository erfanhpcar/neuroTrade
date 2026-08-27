# Frontend Agent Instructions

These instructions extend the root `AGENTS.md` for `frontend/**`.

## TypeScript and Next.js

- Use strict TypeScript. Avoid `any`; if unavoidable at an external boundary, isolate it and validate/narrow immediately.
- Prefer Server Components by default; use Client Components only when browser state/effects/interactivity require them.
- Keep trading/business decisions out of React components. The UI displays state and sends explicit operator commands; Strategy/Risk logic lives in the backend.
- Keep REST/WebSocket types aligned with `docs/10_REST_API.md`; do not create conflicting local enums or magic strings.
- Centralize API access and error handling in the frontend data layer rather than scattering raw fetch calls through components.

## Realtime state

- WebSocket is not the source of truth. On reconnect or sequence gap, resync authoritative state through REST.
- Handle stale worker/data states visibly. Never present stale trading state as healthy/current.
- Reconnect with bounded exponential backoff + jitter and avoid duplicate event application.
- Dangerous actions must show server-confirmed results; optimistic UI must not imply an order/position is changed before confirmation.

## Trading safety UX

- Clearly display `PAPER`, `SEMI`, and `FULL` modes; never make live mode visually ambiguous.
- `HALT` and `FLATTEN ALL` are distinct controls.
- `FLATTEN ALL` requires strong/double confirmation and must state what will be canceled/closed.
- Never expose API secrets in browser bundles, `NEXT_PUBLIC_*`, localStorage, logs, or error messages.
- Private exchange credentials belong only in backend/server secret storage.

## Components and styling

- Use shadcn/ui + Tailwind as defined in project docs.
- Prefer small, accessible components with clear loading/empty/error/stale states.
- Do not encode status only by color; include text/icon semantics.
- Tables and numeric views must format price/quantity/PnL consistently without changing the underlying numeric precision.

## Tests and checks

- Add focused tests for state reducers/hooks and safety-critical dialogs/workflows.
- Test WebSocket reconnect/resync behavior and stale-state presentation.
- Run the repository-defined frontend lint, typecheck, tests, and build checks before completion.
