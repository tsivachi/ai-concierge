# Implementation Plan: 30-Day Personalized AI Concierge

**Branch**: `001-ai-onboarding-concierge` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-onboarding-concierge/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a modular-monolith hackathon MVP that enrolls every new postpaid/prepaid wireless line into a 30-day, account-level onboarding journey with line-level activity tracking; deterministically computes health scores, next-best-actions, and escalations from that state; lets an AI concierge (grounded by local RAG over curated wireless knowledge, and bounded to a read-only Context DTO) explain and personalize — but never decide or mutate; and demonstrates the resulting POCR/PORR intervention story through 11 seeded, resettable demo scenarios in a single-page React demo backed by a FastAPI service, all runnable locally with mock providers and no live external dependencies.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.x (frontend, via React 18 + Vite)
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0 (repository-pattern data access), Chroma (local embedded vector store), React + Vite, httpx (test client + optional real-LLM HTTP calls)
**Storage**: SQLite (file-based, default for local demo) behind a repository interface that also admits PostgreSQL without changing calling code; Chroma's local persistent client for knowledge embeddings
**Testing**: pytest + httpx `TestClient`/`ASGITransport` for backend unit/integration/E2E; Vitest + React Testing Library for lightweight frontend smoke tests
**Target Platform**: Local developer machine (macOS/Linux/Windows) via direct `uvicorn`/`vite` processes, or Docker Compose; single-reviewer demo session, no deployment target beyond local
**Project Type**: Web application (FastAPI backend + React/Vite frontend), organized as a modular monolith
**Performance Goals**: None beyond "feels instant" for a single local reviewer session (sub-200ms typical API responses on a laptop); this MVP is not scale- or latency-engineered — see Constitution Principle IX
**Constraints**: Fully local-first (Constitution Principle VII) — no required network calls; optional real LLM adapter only activates if an API key env var is present, and the system MUST remain fully functional (via `StubLLMProvider`) without one; every external dependency MUST go through a provider interface with a seeded deterministic mock (Constitution Principle II)
**Scale/Scope**: 11 curated demo scenarios, a handful of seeded accounts/lines per scenario, single concurrent reviewer — not a multi-tenant or high-concurrency system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Plan Compliance |
|---|-----------|------------------|
| I | Deterministic Business Logic Before AI | `src/concierge/decisioning` (NBA ranking, health scoring, activity transitions) and `src/concierge/journey` (state machine) are pure/deterministic and contain zero LLM calls. The LLM (`src/concierge/conversation`) only ever receives an already-finalized, read-only `ConciergeContext` DTO and a whitelisted supported-action list; it cannot write to persistence. See Design Rules below and `data-model.md`. PASS |
| II | Mock-First Integrations | `src/concierge/providers` defines a `Protocol` per external dependency (Customer, Order, Billing, Notification, Support, RiskScoring, LLM, Embedding) with a deterministic seeded Mock adapter as the default wiring; `StubLLMProvider` requires no API key. PASS |
| III | Account-Level Journey With Line-Level State | `src/concierge/journey` models one `AccountJourney` aggregate composed of independent `LineOnboardingState` children; journey-level status/health is always derived from line-level state (never stored separately). PASS |
| IV | Privacy Boundary | `apps/api` enforces an auth dependency on every customer-specific route (`/journeys/*`, `/chat` in authenticated mode, `/escalations`); unauthenticated requests can only reach generic knowledge search and generic chat. See `contracts/openapi.yaml`. PASS |
| V | Explainability | `decisioning` returns a `ReasonCode` list alongside every `HealthScore` and `NextBestAction`; API schemas make reason codes non-optional fields, not an afterthought. PASS |
| VI | Idempotent Event Processing and Auditable State Transitions | `src/concierge/events` persists a `processed_events` table keyed by `event_id` (unique constraint) checked before any state mutation; every activity/health/NBA-affecting change is written as an append-only `StateTransitionLog` row. PASS |
| VII | Local-First Demo | SQLite default DB, Chroma local persistent client, `StubLLMProvider` default, seeded JSON/YAML scenarios, both a direct-run path (`uvicorn` + `vite dev`) and an optional `docker-compose.yml`. PASS |
| VIII | Test Core Rules Before Polish | Test Strategy (below) sequences unit tests for domain rules and integration/E2E scenario tests ahead of UI styling polish tasks; `/speckit.tasks` MUST preserve this ordering. PASS |
| IX | Simple Architecture Over Microservices | Single deployable `apps/api` FastAPI service importing `src/concierge/*` modules in-process; single `apps/web` SPA. No network hop between modules. PASS |
| X | Labeled Simulated Metrics | `src/concierge/analytics` computes POCR/PORR intervention counts and the dashboard contract/response schema carries a mandatory `simulated: true` / label field rendered by the UI wherever those figures appear. PASS |

No violations identified. Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-onboarding-concierge/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── openapi.yaml
├── checklists/
│   ├── requirements.md
│   └── mvp-guardrails.md
└── tasks.md              # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/concierge/
├── domain/              # Shared value objects, enums (ActivityStatus, RequirementClass, HealthBand...), pure types with no I/O
├── journey/              # AccountJourney/LineOnboardingState aggregate, activity catalog, JourneyOrchestrator (application coordinator)
├── events/                # Event schema, idempotent ingestion (processed_events dedupe), StateTransitionLog, dead-letter handling
├── decisioning/          # Pure functions: NBA candidate generation + ranking + tie-break, health-score computation, contact-policy (caps/quiet-hours/consent/escalation-suppression)
├── conversation/         # ConciergeContext DTO assembly, prompt construction, LLMProvider invocation, troubleshooting-attempt tracking, escalation-summary generation
├── knowledge/            # Curated knowledge documents, EmbeddingProvider-backed ingestion into Chroma, retrieval/search
├── providers/             # Protocol definitions + Mock*Provider implementations + StubLLMProvider (+ optional real LLM adapter)
├── analytics/            # Dashboard aggregation, POCR/PORR simulated-metric computation
└── persistence/          # SQLAlchemy 2.0 models + repository implementations (SQLite default, Postgres-compatible)

apps/api/
├── main.py                # FastAPI app assembly, provider wiring/DI, middleware (correlation-id, structured logging)
├── routers/               # events, journeys, chat, escalations, dashboard, knowledge, demo, auth
├── deps.py                 # auth dependency (authenticated vs. unauthenticated), provider dependency injection
└── schemas/                # Pydantic request/response models (mirrors contracts/openapi.yaml)

apps/web/
├── src/
│   ├── pages/               # Journey view, Dashboard, Chat, Escalation result
│   ├── components/          # JourneyTimeline, HealthBadge, NBACard, EventInjector, BillingCard, KpiTiles
│   ├── theme/                # theme-tokens.css (CSS custom properties) — swappable brand layer, no hard-coded colors in components
│   └── api/                  # typed fetch client generated/hand-written against openapi.yaml
└── tests/                   # Vitest + React Testing Library smoke tests

seeds/
└── scenarios/              # 11 curated demo scenarios as JSON/YAML (accounts, lines, simulated journey day, pre-existing events)

knowledge_base/
└── *.md                    # 14 curated wireless knowledge documents (activation, eSIM/SIM, porting, voicemail, app, security, billing, first bill, AutoPay, auto-recharge, device protection, network troubleshooting, plan/data use, international usage, prepaid renewal)

tests/
├── unit/                    # journey templates/state transitions, idempotency, NBA ranking, contact policy, health score, billing arithmetic, auth boundary
├── integration/             # event → state → health → NBA; chat context/RAG; escalation; scenario reset (API-level, TestClient)
└── e2e/                      # postpaid activation failure, prepaid renewal, multi-line journey, opt-out, human escalation (full scenario walk-throughs)

docs/
├── architecture.md          # Mermaid module/architecture diagram
└── sequences.md              # Mermaid sequence diagrams (event ingestion, NBA+outreach, chat+RAG, escalation)

docker-compose.yml            # optional: api + web services
README.md                     # architecture summary, setup, run commands, seeded users/scenarios, API examples, judge demo script
```

**Structure Decision**: Web application layout (FastAPI backend + React/Vite frontend) organized as a single modular-monolith Python package (`src/concierge/*`, imported directly by `apps/api`) plus one SPA (`apps/web`), matching the user-specified module boundaries. No inter-module network calls or separate deployables — consistent with Constitution Principle IX.

## Complexity Tracking

> Not applicable — no Constitution Check violations to justify.
