# 30-Day Personalized AI Concierge

A hackathon MVP that reverses the standard wireless support model: instead of waiting for a new customer to call in or visit retail, this system enrolls every new line into a personalized 30-day onboarding journey, deterministically detects friction and computes the next best action, proactively guides the customer, resolves common issues via an AI concierge grounded in real account state, and escalates to a human with full context when needed — demonstrating (simulated) reductions in post-online call rate (POCR) and post-online retail rate (PORR).

See [docs/architecture.md](docs/architecture.md) for the module diagram and [docs/sequences.md](docs/sequences.md) for key flows.

## Architecture Summary

Modular monolith (Constitution Principle IX): one FastAPI service (`apps/api`) importing a pure Python domain package (`src/concierge/*`), plus one React/Vite SPA (`apps/web`). SQLite + a local Chroma vector store; no live external services required. Every external dependency (customer, order, billing, notification, support, risk-scoring, LLM, embeddings) sits behind a `Protocol` with a deterministic seeded mock — the app is fully functional with zero API keys.

Business logic (health scoring, next-best-action ranking, contact policy, escalation triggers) is 100% deterministic Python — the AI/LLM layer only explains or personalizes wording for decisions the deterministic core already finalized. It never mutates state, computes a bill, bypasses consent, or invents a fact.

Every backend capability, billing/renewal included, is implemented and covered by 257 passing `pytest` tests. The React UI (`apps/web`) has been run end-to-end against the live API — scenario load, journey/health/NBA rendering, chat + escalation, and billing/renewal all verified in-browser — with its 9 Vitest component tests passing.

## Prerequisites

- Python 3.12+
- Node.js 20+ (for `apps/web`)
- Internet access on first run only, to download the local embedding model (~80MB, cached after)
- No API keys required — `ANTHROPIC_API_KEY` is optional (see below)

## Run Commands

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn apps.api.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open the printed Vite URL (typically http://localhost:5173).

### Optional: real LLM instead of the deterministic stub

```bash
export ANTHROPIC_API_KEY=sk-...
# restart uvicorn
```

Without this, `StubLLMProvider` answers deterministically — the whole app, including chat and escalation, works identically either way.

### Docker Compose (optional)

```bash
docker compose up --build
```

### Tests

```bash
pytest                 # 257 backend tests: unit + integration + e2e
cd apps/web && npm test  # 9 frontend component tests (Vitest)
```

## Seeded Demo Scenarios

Each scenario resets the entire database to a clean, deterministic starting state — backdated so day-3/5/7/10/21 thresholds are already true on load (no waiting required).

| # | Scenario ID | What it demonstrates |
|---|---|---|
| 1 | `postpaid-device-port-in` | New postpaid line + number port, golden-path enrollment |
| 2 | `prepaid-byod-esim` | New prepaid BYOD line, eSIM, no port |
| 3 | `multi-line-postpaid` | Two lines on one account journey, independent per-line NBA |
| 4 | `repeated-activation-failure` | Activation failure → health/NBA impact → escalation |
| 5 | `delayed-failed-port` | Number transfer stuck pending too long |
| 6 | `app-adoption-gap-day3` | Day-3+ recommended-activity nudge (app download) |
| 7 | `postpaid-first-bill-day21` | Day-21 postpaid checkpoint |
| 8 | `prepaid-renewal-approaching` | Prepaid line past the auto-recharge gap threshold, with renewal readiness visible via `GET /journeys/{id}/billing` |
| 9 | `contextual-troubleshooting` | Authenticated chat explaining a real NBA, grounded in RAG |
| 10 | `human-escalation-with-context` | Unresolved activation failure escalates automatically |
| 11 | `customer-opt-out` | Opted-out customer receives zero proactive outreach |

Each scenario's `customer_id` is returned in the reset response — use it to log in.

## API Examples

```bash
# List scenarios
curl http://localhost:8000/api/demo/scenarios

# Reset one and capture its journey/customer ids
curl -X POST http://localhost:8000/api/demo/scenarios/repeated-activation-failure/reset

# Log in as the seeded customer
curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" \
  -d '{"customer_id": "cust-repeated-failure"}'

# View journey / health / recommendation (replace TOKEN and JOURNEY_ID)
curl http://localhost:8000/api/journeys/JOURNEY_ID -H "Authorization: Bearer TOKEN"
curl http://localhost:8000/api/journeys/JOURNEY_ID/health -H "Authorization: Bearer TOKEN"
curl http://localhost:8000/api/journeys/JOURNEY_ID/recommendation -H "Authorization: Bearer TOKEN"

# Chat (authenticated) — automatically escalates for an unresolved activation failure
curl -X POST http://localhost:8000/api/chat -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"session_id": "demo-1", "message": "why does my phone still not work?"}'

# Generic help, unauthenticated
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"session_id": "demo-2", "message": "how do I set up voicemail?"}'

# Aggregate outcome dashboard (always simulated/projected, always labeled)
curl http://localhost:8000/api/dashboard
```

## Judge Demo Script (5-7 minutes)

1. **Golden path — Scenario 1** (`postpaid-device-port-in`, ~1 min): Reset the scenario in the UI, show the Journey tab — every required activity starts `NOT_STARTED`. Inject `DeviceActivationStarted` → `DeviceActivationCompleted` via the Event Injector; watch the activity flip to `COMPLETED` live, no page reload.

2. **Friction + escalation — Scenario 4** (`repeated-activation-failure`, ~1.5 min): Reset it; Health tab shows a YELLOW/RED band with an `ACTIVATION_FAILURE` reason code; NBA tab shows priority 100 with a personalized message. Switch to Chat, log in, ask "why does my phone still not work?" — the concierge escalates automatically; open the Escalation panel to show the case bundles the failure history, no re-explaining needed.

3. **Prepaid adoption + renewal readiness — Scenario 8** (`prepaid-renewal-approaching`, ~1 min): Reset it; NBA shows the auto-recharge gap (priority 60, correctly below any critical issue); the Billing card shows balance/renewal date/auto-recharge state with a plain-language explanation, clearly marked "not a final renewal confirmation." Ask the chat "how do I turn on auto-recharge?" — grounded answer citing the auto-recharge knowledge article.

4. **Contextual AI troubleshooting — Scenario 9** (`contextual-troubleshooting`, ~1.5 min): Log in as the seeded customer, ask "what is my next step?" (explains the real NBA) and "how long does porting my number take?" (grounded in the porting knowledge doc, source cited). Try "please cancel my line" — show it refuses to claim the action and escalates instead, rather than fabricating a "done."

5. **Human escalation with full context — Scenario 10** (`human-escalation-with-context`, ~1 min): Reset it, ask the concierge anything; show the resulting `EscalationCase` already contains the journey snapshot, relevant event ids, and a conversation summary — a human agent needs nothing repeated.

6. **Dashboard — ~30 sec**: Open the Dashboard tab; point out every count reflects real seeded state, and the POCR/PORR tiles are visibly marked **SIMULATED / PROJECTED** — never presented as a measured result.

## Verified

- `pytest` → 257 passed (unit, integration, e2e) — every task in `specs/001-ai-onboarding-concierge/tasks.md` is implemented (152/152).
- `cd apps/web && npm test` → 9 passed (Vitest component tests).
- Manually driven end-to-end in a live browser against the running API: scenario reset, authenticated login, journey timeline/health/NBA rendering, event injection, chat with RAG-grounded answers and auto-escalation, and the postpaid/prepaid billing card — all confirmed working against real (mock-backed) data, not just unit-tested in isolation.
