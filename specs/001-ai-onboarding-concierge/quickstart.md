# Quickstart: 30-Day Personalized AI Concierge

This validates that a clean checkout can run the full demo locally with only mocked/seeded data (Constitution Principle VII, spec SC-010). It is the source for the polished `README.md` deliverable, not a replacement for it.

## Prerequisites

- Python 3.12+
- Node.js 20+ (for `apps/web`)
- (Optional) Docker + Docker Compose
- No API keys required. `ANTHROPIC_API_KEY` is optional — if unset, `StubLLMProvider` is used and the concierge chat still fully functions (deterministic templated answers, still grounded by RAG).

## Option A — Direct local run

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn apps.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd apps/web
npm install
npm run dev
```

Open the printed Vite URL (typically `http://localhost:5173`). The FastAPI OpenAPI docs are at `http://localhost:8000/docs`.

## Option B — Docker Compose

```bash
docker compose up --build
```

Brings up `api` (port 8000) and `web` (port 5173) with SQLite/Chroma data persisted in local volumes.

## Seeding & demo scenarios

On first startup, `apps/api` creates the SQLite schema and ingests `knowledge_base/*.md` into the local Chroma collection. Demo scenarios are **not** auto-loaded — select one explicitly so state stays deterministic:

```bash
curl http://localhost:8000/api/demo/scenarios
curl -X POST http://localhost:8000/api/demo/scenarios/postpaid-device-port-in/reset
```

The 11 seeded scenario ids (see `seeds/scenarios/`, matching `spec.md §Demo Scenario Catalog`):

1. `postpaid-device-port-in`
2. `prepaid-byod-esim`
3. `multi-line-postpaid`
4. `repeated-activation-failure`
5. `delayed-failed-port`
6. `app-adoption-gap-day3`
7. `postpaid-first-bill-day21`
8. `prepaid-renewal-approaching`
9. `contextual-troubleshooting`
10. `human-escalation-with-context`
11. `customer-opt-out`

Each scenario's seeded demo customer_id is printed in the reset response and listed in `README.md`.

## Exercising the golden path (Scenario 1)

```bash
# 1. Reset to the scenario's starting state
curl -X POST http://localhost:8000/api/demo/scenarios/postpaid-device-port-in/reset

# 2. Inject the activation events (journey_id comes from the reset response)
curl -X POST http://localhost:8000/api/events -d '{"event_id":"evt-1","event_type":"DeviceActivationStarted", ...}'
curl -X POST http://localhost:8000/api/events -d '{"event_id":"evt-2","event_type":"DeviceActivationCompleted", ...}'

# 3. Observe state
curl http://localhost:8000/api/journeys/{journey_id}
curl http://localhost:8000/api/journeys/{journey_id}/recommendation
curl http://localhost:8000/api/journeys/{journey_id}/health

# 4. Log in as the seeded customer and ask the concierge about it
curl -X POST http://localhost:8000/api/auth/login -d '{"customer_id":"cust-demo-1"}'
curl -X POST http://localhost:8000/api/chat -H "Authorization: Bearer <token>" \
  -d '{"session_id":"s1","message":"what do I still need to do?"}'
```

## Running tests

```bash
pytest                       # unit + integration + e2e (tests/unit, tests/integration, tests/e2e)
cd apps/web && npm test       # Vitest smoke tests
```

`tests/unit` and `tests/integration` MUST pass before any UI-polish task is considered done (Constitution Principle VIII).

## Validation checklist for this quickstart

- [ ] Clean checkout → direct-run steps above succeed with zero manual config beyond installing dependencies
- [ ] Docker Compose path also succeeds independently
- [ ] All 11 scenarios reset without residual state from a prior scenario (spec SC-011)
- [ ] Chat works with `ANTHROPIC_API_KEY` unset (StubLLMProvider path)
- [ ] Dashboard's POCR/PORR figures render with a visible "simulated/projected" label (spec SC-009)
